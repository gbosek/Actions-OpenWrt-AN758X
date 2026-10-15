#!/usr/bin/env python3
"""Verify three upstream fixes and exercise the actual TRTCM retry function."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


def function(text, name):
    start = re.search(r'\bstatic\s+[^;{}]*\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{', text)
    assert start, 'Missing function: ' + name
    depth, end = 1, start.end()
    while depth and end < len(text):
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    assert depth == 0
    return text[start.start():end]


PREFIX = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
typedef uint32_t u32;
#define EBUSY 16
#define USEC_PER_MSEC 1000
#define FIELD_PREP(mask, val) (((u32)(val) << __builtin_ctz(mask)) & (mask))
#define QDMA_METER_IDX(v) ((v) & 0xf)
#define QDMA_METER_GROUP(v) ((v) >> 4)
#define TRTCM_PARAM_RW_MASK 0x80000000u
#define TRTCM_PARAM_TYPE_MASK 0x03000000u
#define TRTCM_METER_GROUP_MASK 0x00f00000u
#define TRTCM_PARAM_INDEX_MASK 0x000f0000u
#define TRTCM_PARAM_RATE_TYPE_MASK 0x00003000u
#define TRTCM_PARAM_RW_DONE_MASK 0x40000000u
#define REG_TRTCM_DATA_LOW(addr) ((addr) + 4)
#define REG_TRTCM_CFG_PARAM(addr) ((addr) + 8)
enum trtcm_param_type { TEST_PARAM = 1 };
enum trtcm_mode_type { TEST_MODE = 1 };
struct airoha_qdma { int polls, reads, writes, bad_write; int poll_error[2], read_error[2]; u32 read_value[2], expected; };
static void airoha_qdma_wr(struct airoha_qdma *q, u32 reg, u32 value) {
    q->writes++;
    if (reg == REG_TRTCM_DATA_LOW(100) && value != q->expected) q->bad_write++;
}
static int fixture_poll(struct airoha_qdma *q, u32 *value) {
    int i = q->polls++; *value = TRTCM_PARAM_RW_DONE_MASK;
    return q->poll_error[i];
}
#define read_poll_timeout(fn, value, cond, delay, timeout, sleep, q, reg) fixture_poll(q, &(value))
static int airoha_qdma_get_trtcm_param(struct airoha_qdma *q, int ch, u32 addr, enum trtcm_param_type p, enum trtcm_mode_type m, u32 *value, void *high) {
    (void)ch; (void)addr; (void)p; (void)m; (void)high;
    int i = q->polls - 1; q->reads++; *value = q->read_value[i]; return q->read_error[i];
}
'''
CASES = r'''
int main(void) {
    int cases = 0, failures = 0;
    for (int scenario = 0; scenario < 7; scenario++) {
        struct airoha_qdma q = {.expected = 0x12345, .read_value = {0x12345, 0x12345}};
        int expected = 0, polls = scenario == 0 ? 1 : 2;
        switch (scenario) {
        case 1: q.poll_error[0] = -110; break;
        case 2: q.read_error[0] = -5; break;
        case 3: q.read_value[0] = 0x99999; break;
        case 4: q.poll_error[0] = q.poll_error[1] = -110; expected = -EBUSY; break;
        case 5: q.read_error[0] = q.read_error[1] = -5; expected = -EBUSY; break;
        case 6: q.read_value[0] = q.read_value[1] = 0x99999; expected = -EBUSY; break;
        }
        int result = airoha_qdma_set_trtcm_param(&q, 7, 100, TEST_PARAM, TEST_MODE, q.expected);
        cases++;
        if (result != expected || q.polls != polls || q.writes != polls * 2 || q.bad_write) failures++;
    }
    printf("{\"cases\":%d,\"failures\":%d}\n", cases, failures);
    return failures != 0;
}
'''


def verify(kernel, compiled=False, object_dir=None):
    directory = kernel / 'drivers/net/ethernet/airoha'
    eth, header, npu = [(directory / name).read_text() for name in ('airoha_eth.c', 'airoha_eth.h', 'airoha_npu.c')]
    limit = re.search(r'^#define\s+TRTCM_CONFIG_RETRY_MAX\s+(\d+)', header, re.M)
    assert limit and limit[1] == '2', 'TRTCM retry limit missing'
    mask = re.search(r'^#define\s+RX_IRQ1_BANK_PIN_MASK\s+(0x[0-9a-fA-F]+)', header, re.M)
    assert mask and int(mask[1], 16) == 0xffe00000, 'RX queue31 interrupt not enabled'
    assert '#include <linux/devm-helpers.h>' in npu
    probe = function(npu, 'airoha_npu_probe')
    begin = probe.index('devm_work_autocancel(dev, &core->wdt_work,')
    request = probe.index('devm_request_irq(dev, irq, airoha_npu_wdt_handler,')
    assert begin < request, 'Watchdog work initialized after its interrupt'
    assert 'INIT_WORK(&core->wdt_work' not in npu
    assert 'airoha_npu_remove' not in npu, 'Old watchdog teardown remains'
    with tempfile.TemporaryDirectory(prefix='airoha-trtcm-test-') as temp:
        cfile, binary = Path(temp) / 'test.c', Path(temp) / 'test'
        cfile.write_text(PREFIX + '\n#define TRTCM_CONFIG_RETRY_MAX ' + limit[1] + '\n' + function(eth, 'airoha_qdma_set_trtcm_param') + CASES)
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', str(cfile), '-o', str(binary)], check=True)
        results = json.loads(subprocess.check_output([str(binary)], text=True))
    assert results == {'cases': 7, 'failures': 0}
    if compiled:
        objects = object_dir or directory
        for name in ('airoha_eth.o', 'airoha_npu.o'):
            data = (objects / name).read_bytes()
            assert data[:4] == b'\x7fELF' and int.from_bytes(data[18:20], 'little') == 183, 'Missing ARM64 driver: ' + name
        assert b'devm_work_drop' in (objects / 'airoha_npu.o').read_bytes(), 'Compiled NPU cleanup helper missing'
    report = {'kernel': kernel.name, 'trtcm_cases': results['cases'], 'rx31_irq': True,
              'watchdog_cleanup_order': True, 'compiled_arm64': compiled,
              'source_sha256': {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in ('airoha_eth.c', 'airoha_eth.h', 'airoha_npu.c')},
              'scope': 'Actual TRTCM function with host bus/readback fixtures; source and ARM64 object checks; hardware stability requires device testing'}
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--kernel', type=Path)
    group.add_argument('--build-dir', type=Path)
    parser.add_argument('--compiled', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--object-dir', type=Path, help='Separate O= output for local cross-compilation validation')
    args = parser.parse_args()
    if args.kernel:
        kernel = args.kernel
    else:
        found = [p for p in args.build_dir.glob('target-*/linux-*/linux-6.18.*') if (p / 'drivers/net/ethernet/airoha/airoha_eth.c').is_file()]
        assert len(found) == 1, 'Expected one actual prepared Airoha kernel'
        kernel = found[0]
    report = verify(kernel, args.compiled, args.object_dir)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
