#!/usr/bin/env python3
"""Exercise actual prepared PPE functions with host-side entry/ACK fixtures."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


def find_kernel(build_dir):
    # target/linux/prepare extracts and patches sources before kernel configure
    # creates .config.  The post-build gate checks the actual configuration.
    sources = build_dir.glob('target-*/linux-*/linux-6.18.*/drivers/net/ethernet/airoha/airoha_ppe.c')
    kernels = sorted({p.parents[4] for p in sources
                      if (p.parent / 'airoha_eth.h').is_file()})
    if len(kernels) != 1:
        raise ValueError(f'Expected one prepared 6.18 kernel with PPE source/header in {build_dir}, found {len(kernels)}')
    return kernels[0]


def function(text, name):
    declaration = re.search(r'\bstatic\s+[^;{}]*\b' + re.escape(name)
                            + r'\s*\([^;{}]*\)\s*\{', text)
    if not declaration:
        raise ValueError(f'Function definition missing: {name}')
    end = declaration.end()
    depth = 1
    while depth and end < len(text):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
        end += 1
    if depth:
        raise ValueError(f'Function body incomplete: {name}')
    return text[declaration.start():end]


PREFIX = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
typedef uint32_t u32;
#define FIELD_GET(mask,v) (((v)&(mask)) >> __builtin_ctz(mask))
#define AIROHA_FOE_IB1_BIND_STATE 0x30000000u
#define AIROHA_FOE_STATE_BIND 2
#define AIROHA_FOE_IB1_BIND_PACKET_TYPE 0x0e000000u
#define AIROHA_FOE_IB1_BIND_TIMESTAMP 0x00007fffu
#define FLOW_TYPE_L2 1
struct airoha_foe_entry { u32 ib1; };
struct airoha_flow_table_entry { int type; unsigned hash; struct airoha_foe_entry data; };
struct airoha_ppe { struct airoha_foe_entry *foe; int fail_at; unsigned commits; };
static int ppe_lock, l2_calls;
static bool fixture_match;
static void spin_lock_bh(int *x) { (void)x; }
static void spin_unlock_bh(int *x) { (void)x; }
static struct airoha_foe_entry *airoha_ppe_foe_get_entry_locked(struct airoha_ppe *p, unsigned h)
{ return h == 0xfffe ? NULL : p->foe; }
static bool airoha_ppe_foe_compare_entry(struct airoha_flow_table_entry *e, struct airoha_foe_entry *h)
{ (void)e; (void)h; return fixture_match; }
static void airoha_ppe_foe_flow_l2_entry_update(struct airoha_ppe *p, struct airoha_flow_table_entry *e)
{ (void)p; (void)e; l2_calls++; }
static u32 airoha_ppe_get_total_sram_num_entries(struct airoha_ppe *p) { (void)p; return 4; }
static int airoha_ppe_foe_commit_sram_entry(struct airoha_ppe *p, u32 h)
{ p->commits++; return (int)h == p->fail_at ? -110 : 0; }
'''

TESTS = r'''
int main(void) {
    int failures = 0, cases = 0;
    struct airoha_foe_entry hw[4] = {{0}};
    struct airoha_ppe p = {.foe = hw, .fail_at = -1};
    const u32 template = 0x624b1234u;
    struct airoha_flow_table_entry e = {.type = 0, .hash = 7, .data = {template}};
    fixture_match = true;
    hw[0].ib1 = 0x123abc42u; /* UNB count must not overwrite the TC template. */
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.data.ib1 != template) failures++;
    e.data.ib1 = template;
    hw[0].ib1 = 0x22000077u; /* BND with different encapsulation flags. */
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.data.ib1 != ((template & ~0x7fffu) | 0x77u)) failures++;
    e.data.ib1 = template;
    hw[0].ib1 = 0x24000077u; /* A different packet type cannot refresh it. */
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.data.ib1 != template) failures++;
    e.data.ib1 = template;
    hw[0].ib1 = 0x32000077u; /* A non-BIND state cannot refresh it. */
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.data.ib1 != template) failures++;
    e.data.ib1 = template; fixture_match = false;
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.hash != 0xffff || e.data.ib1 != template) failures++;
    fixture_match = true; e.hash = 0xffff;
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.data.ib1 != template) failures++;
    e.hash = 0xfffe;
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (e.data.ib1 != template) failures++;
    e.type = FLOW_TYPE_L2; e.hash = 7;
    airoha_ppe_foe_flow_entry_update(&p, &e);
    cases++; if (l2_calls != 1 || e.data.ib1 != template) failures++;
    for (int fail = -1; fail <= 2; fail++) {
        p.fail_at = fail; p.commits = 0;
        int result = airoha_ppe_flush_sram_entries(&p);
        cases++; if (result != (fail < 0 ? 0 : -110)) failures++;
        cases++; if (p.commits != (unsigned)(fail < 0 ? 4 : fail + 1)) failures++;
    }
    printf("{\"cases\":%d,\"failures\":%d}\n", cases, failures);
    return 0;
}
'''


def check(kernel):
    driver = kernel / 'drivers/net/ethernet/airoha'
    header = (driver / 'airoha_eth.h').read_text()
    for name, high, low in [('STATE', 29, 28), ('PACKET_TYPE', 27, 25), ('TIMESTAMP', 14, 0)]:
        pattern = rf'#define\s+AIROHA_FOE_IB1_BIND_{name}\s+GENMASK\({high},\s*{low}\)'
        if not re.search(pattern, header):
            raise ValueError(f'Fixture incompatible with IB1 {name} layout')
    source = (driver / 'airoha_ppe.c').read_text()
    bodies = '\n'.join(function(source, name) for name in
                       ('airoha_ppe_foe_flow_entry_update', 'airoha_ppe_flush_sram_entries'))
    with tempfile.TemporaryDirectory(prefix='ppe-functions-') as directory:
        cfile = Path(directory) / 'fixture.c'
        binary = Path(directory) / 'fixture'
        cfile.write_text(PREFIX + bodies + TESTS)
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-Wno-sign-compare', str(cfile), '-o', str(binary)], check=True)
        result = json.loads(subprocess.check_output([str(binary)], text=True))
    result['source_sha256'] = hashlib.sha256((driver / 'airoha_ppe.c').read_bytes()).hexdigest()
    result['scope'] = 'Actual function bodies with host lock/entry/ACK fixtures; no hardware validation'
    print(json.dumps(result))
    if result['cases'] != 16 or result['failures']:
        raise ValueError('PPE candidate function regression failed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--build-dir', type=Path)
    group.add_argument('--kernel', type=Path)
    args = parser.parse_args()
    try:
        check(args.kernel if args.kernel else find_kernel(args.build_dir))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'PPE function check failed: {error}\n')


if __name__ == '__main__':
    main()
