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
assert 'cpucores: cores' in backend.read_text(), 'Per-core CPU RPC absent'
assert 'renderCPUCoreUsage(cpuusage)' in page.read_text(), 'Per-core CPU overview absent'
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
assert b'cpucores' in (installed / 'usr/share/rpcd/ucode/luci').read_bytes()
assert 'cpucores' in (installed / 'www/luci-static/resources/view/status/include/10_system.js').read_text()
for name in ('airoha-npu', 'xg2010g-rps'):
    path = installed / 'etc/init.d' / name
    assert path.is_file() and path.stat().st_mode & 0o111, f'Service not executable: {name}'
print('Latest Airoha snapshot, MWAN4, Chinese UI, four CPU cores and RPS recovery verified in staged rootfs')
