"""Check actual prepared driver egress selection with a host C fixture.

This exercises the driver's condition and port expression, not hardware queues.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
review = repo.parent / 'output/GitHub24-review'
build = Path('/home/bosek/xg2010g-local-build/ponwrt-5615b88-clean')
driver = build / 'build_dir/target-aarch64_cortex-a53_musl/linux-airoha_an7581/linux-6.18.52/drivers/net/ethernet/airoha'
ppe = (driver / 'airoha_ppe.c').read_text()
eth = (driver / 'airoha_eth.c').read_text()
header = (driver / 'airoha_eth.h').read_text()
begin = ppe.index('\t\t\tif (dsa_port >= 0 || eth->ports[1] || airoha_is_lan_gdm_dev(dev))')
end = ppe.index('\n\n', begin)
branch = ppe[begin:end]
constants = re.search(r'enum \{\s*FE_PSE_PORT_CDM1,.*?\n\};', header, re.S).group()
begin = eth.index('static int airoha_set_direct_hw_wan1(')
end = eth.index('\nstatic ', begin + 1)
selector = eth[begin:end]
assert 'airoha_enable_gdm2_loopback' not in selector
assert 'airoha_dev_set_qdma' not in selector
assert not re.search(r'dev->flags\s*[|&]?=', selector), 'direct WAN1 changed logical WAN role'
assert selector.index('airoha_ppe_remove_egress_flows(dev);') < selector.index('REG_FE_WAN_PORT')
assert 'dev->hw_wan_slot = AIROHA_HW_WAN1;' in selector
assert 'FIELD_PREP(WAN_MTU1_MASK, netdev->mtu + VLAN_ETH_HLEN)' in eth
source = '''#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
''' + constants + '''
struct airoha_eth { void *ports[2]; };
struct airoha_gdm_dev { bool lan; };
struct airoha_gdm_port { int id; };
static bool airoha_is_lan_gdm_dev(struct airoha_gdm_dev *dev) { return dev->lan; }
static int select_port(int dsa_port, bool gdm2_present, bool lan, int id) {
    struct airoha_eth device = { .ports = { NULL, gdm2_present ? &device : NULL } };
    struct airoha_gdm_dev netdev = { .lan = lan };
    struct airoha_gdm_port physical = { .id = id };
    struct airoha_eth *eth = &device;
    struct airoha_gdm_dev *dev = &netdev;
    struct airoha_gdm_port *port = &physical;
    int pse_port;
''' + branch + '''
    return pse_port;
}
int main(void) {
    assert(FE_PSE_PORT_GDM2 == 2);
    assert(FE_PSE_PORT_GDM3 == 3);
    assert(FE_PSE_PORT_GDM4 == 9);
    for (int lan = 0; lan <= 1; ++lan) {
        assert(select_port(-1, true, lan, 3) == FE_PSE_PORT_GDM3);
        assert(select_port(-1, true, lan, 4) == FE_PSE_PORT_GDM4);
    }
    assert(select_port(-1, false, true, 3) == FE_PSE_PORT_GDM3);
    assert(select_port(-1, false, true, 4) == FE_PSE_PORT_GDM4);
    assert(select_port(0, false, false, 4) == FE_PSE_PORT_GDM4);
    assert(select_port(-1, false, false, 3) == FE_PSE_PORT_GDM2);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='gdm2-egress-review-') as directory:
    root = Path(directory)
    program = root / 'egress.c'
    program.write_text(source)
    subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror', '-o', str(root / 'egress'), str(program)], check=True)
    subprocess.run([str(root / 'egress')], check=True)
log = (review / 'build-review.log').read_text()
assert '938-net-airoha-use-direct-egress-when-gdm2-present.patch using plaintext' in log
assert '939-net-airoha-program-mtu-for-runtime-wan1.patch using plaintext' in log
summary = {'result': 'PASS', 'ppe_source_sha256': hashlib.sha256(ppe.encode()).hexdigest(), 'egress_condition': branch.strip(), 'direct_wan1_has_no_loopback_or_qdma_role_change': True, 'gdm4_pse_port': 9, 'gdm3_pse_port': 3, 'scope': 'host C branch fixture and actual prepared source; hardware congestion not measured'}
(review / 'gdm2-egress-check.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print('PASS: actual 938 egress condition, GDM3/GDM4 direct output, legacy loopback fallback, direct WAN1 role and combined 939 MTU fix')
