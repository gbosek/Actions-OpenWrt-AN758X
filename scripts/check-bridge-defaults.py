#!/usr/bin/env python3
"""Verify the staged fw4/default-module fix without running target binaries."""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def check(root):
    meta = json.loads((REPO / 'Offload/bridge-defaults/SOURCE.json').read_text())
    assert json.loads((root / 'etc/airoha-bridge-defaults.json').read_text()) == meta
    helper = root / 'usr/libexec/xg2010g-bridge-netfilter'
    assert helper.read_bytes() == (REPO / 'Offload/bridge-defaults/xg2010g-bridge-netfilter').read_bytes()
    assert helper.stat().st_mode & 0o111, 'Bridge request helper is not executable'
    assert '/usr/libexec/xg2010g-bridge-netfilter || logger -t xg2010g-bridge' in (root / 'etc/init.d/sysctl').read_text()
    fw4 = root / 'usr/share/ucode/fw4.uc'
    template = root / 'usr/share/firewall4/templates/ruleset.uc'
    assert 'flow_offloading_bridge: [ "bool", "0" ]' in fw4.read_text()
    text = template.read_text()
    gate = '{% if (fw4.default_option("flow_offloading_bridge")): %}'
    assert text.count(gate) == 1 and text.index(gate) < text.index('table bridge fw4')
    assert 'table inet fw4' in text and 'flowtable ft' in text
    assert "{% fw4.includes('ruleset-append') %}" in text
    for directory in ('etc/modules.d', 'etc/modules-boot.d'):
        for file in (root / directory).glob('*'):
            assert 'br_netfilter' not in file.read_text(), 'Unconditional bridge compatibility hooks: ' + str(file)
    assert list((root / 'lib/modules').glob('*/br_netfilter.ko*')), 'Demand-load bridge capability missing'
    assert list((root / 'lib/modules').glob('*/nf_conntrack_bridge.ko*')), 'Native bridge CT capability missing'
    default = (root / 'etc/sysctl.d/11-br-netfilter.conf').read_bytes()
    assert hashlib.sha256(default).hexdigest() == meta['packaged_bridge_sysctl_sha256']
    files = ['etc/init.d/sysctl', 'usr/libexec/xg2010g-bridge-netfilter', 'usr/share/ucode/fw4.uc',
             'usr/share/firewall4/templates/ruleset.uc', 'etc/airoha-bridge-defaults.json']
    return {'files': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files},
            'installed_bridge_capabilities': True, 'unconditional_compatibility_hooks': False,
            'hardware_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    roots = list(args.build_dir.glob('target-*/root-airoha'))
    assert len(roots) == 1, 'Expected one staged rootfs'
    result = check(roots[0])
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
