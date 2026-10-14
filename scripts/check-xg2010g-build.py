#!/usr/bin/env python3
"""Reject firmware missing the requested Airoha snapshot or four-core view."""
import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
root = args.source
meta = json.loads((root / 'files/etc/airoha-build-source.json').read_text())
assert meta['commit'] == '323539cf229bce52754fbb318135c9c56c514d2f', 'Airoha source SHA mismatch'
backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
assert "popen('/sbin/cpuusage')" in backend.read_text(), 'Native CPU helper RPC absent'
assert 'cpuusage.cpuusage' in page.read_text(), 'Native CPU overview absent'
manifest_dir = root / 'bin/targets/airoha/an7581'
for manifest in manifest_dir.glob('*.manifest'):
    pkgs = dict(re.findall(r'^(\S+) - (.+)$', manifest.read_text(), re.M))
    for name in ('mwan4', 'luci-app-mwan4', 'luci-i18n-mwan4-zh-cn',
                 'luci-app-airoha-npu', 'luci-i18n-airoha-npu-zh-cn', 'xg2010g-rps'):
        assert name in pkgs, f'{manifest.name}: missing {name}'
    assert pkgs['xg2010g-rps'].startswith('20261013'), 'Old RPS package'
    assert not any(n in pkgs for n in ('mwan3', 'mwan3-nft', 'luci-app-mwan3')), 'Mixed MWAN stacks'
    assert pkgs['luci-app-airoha-npu'].startswith('2.0.0-r9'), 'Unexpected upstream package version'
# Validate installed files before releasing any sysupgrade image.
roots = list((root / 'build_dir').glob('target-*/root-airoha'))
assert len(roots) == 1, f'Expected one staged rootfs, got {len(roots)}'
installed = roots[0]
assert json.loads((installed / 'etc/airoha-build-source.json').read_text()) == meta
assert b"popen('/sbin/cpuusage')" in (installed / 'usr/share/rpcd/ucode/luci').read_bytes()
assert 'cpuusage.cpuusage' in (installed / 'www/luci-static/resources/view/status/include/10_system.js').read_text()
expected_cpu = Path(__file__).resolve().parents[1] / 'files/sbin/cpuusage'
cpu = installed / 'sbin/cpuusage'
assert cpu.is_file() and cpu.stat().st_mode & 0o111, 'Missing executable native CPU usage helper'
assert cpu.read_bytes() == expected_cpu.read_bytes(), 'CPU usage helper differs from repository source'
assert not (installed / 'files/sbin/cpuusage').exists(), 'Nested CPU usage overlay found'
assert 'CPU%d' in cpu.read_text(), 'Per-core labels missing from native helper'
expected_temp = Path(__file__).resolve().parents[1] / 'files/sbin/tempinfo'
temp = installed / 'sbin/tempinfo'
assert temp.is_file() and temp.stat().st_mode & 0o111, 'Missing executable /sbin/tempinfo in rootfs'
assert temp.read_bytes() == expected_temp.read_bytes(), 'Temperature script differs from the requested overlay'
for label in ('CPU:', 'PON:', 'LAN1:', 'LAN2:'):
    assert label in temp.read_text(), f'Missing temperature sensor: {label}'
assert "popen('/sbin/tempinfo')" in (installed / 'usr/share/rpcd/ucode/luci').read_text(), 'RPC temperature path differs'
assert not (installed / 'files/sbin/tempinfo').exists(), 'Nested /files overlay found in rootfs'
for name in ('airoha-npu', 'xg2010g-rps'):
    path = installed / 'etc/init.d' / name
    assert path.is_file() and path.stat().st_mode & 0o111, f'Service not executable: {name}'
print('Latest Airoha snapshot, MWAN4, Chinese UI, four CPU cores, RPS recovery and CPU/PON/LAN1/LAN2 temperature script verified in staged rootfs')
