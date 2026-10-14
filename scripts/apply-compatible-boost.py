#!/usr/bin/env python3
"""Install the reviewed XG2010G compatibility boost implementation."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
a = p.parse_args()
root = a.source.resolve()
repo = Path(__file__).resolve().parents[1]
config = root / 'target/linux/airoha/an7581/config-6.18'
queue = root / 'target/linux/airoha/patches-6.18'
assert config.is_file() and queue.is_dir(), 'Expected AN7581 Linux 6.18 source'
for pattern in ('936*pll*.patch', '937*pll*.patch', '0401*pll*.patch', '0402*pll*.patch'):
    assert not list(queue.glob(pattern)), 'Conflicting direct-PLL implementation'
patchname = '999-xg2010g-bl31-compatible-overclock.patch'
shutil.copyfile(repo / 'kernel-patches/airoha' / patchname, queue / patchname)
board_patch = repo / 'source-patches/airoha/999-xg2010g-compatible-boost-dts.patch'
cmd = ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(root), '-i', str(board_patch)]
forward = subprocess.run(cmd + ['--dry-run'], capture_output=True)
if forward.returncode == 0:
    subprocess.run(cmd, check=True)
else:
    reverse = subprocess.run(cmd + ['--dry-run', '-R'], capture_output=True)
    assert reverse.returncode == 0, 'CPU board patch does not match this source'
text = config.read_text()
for key in ('CONFIG_AIROHA_CPU_PM_DOMAIN', 'CONFIG_CPU_FREQ', 'CONFIG_CPU_FREQ_GOV_ONDEMAND', 'CONFIG_CPU_FREQ_GOV_POWERSAVE', 'CONFIG_SMP'):
    assert re.search(rf'^{key}=y$', text, re.M), f'Missing kernel prerequisite: {key}'
# Keep the common package and helper identical in both NPU variants.
pkg = root / 'package/emortal/cpufreq'
assert (pkg / 'Makefile').is_file(), 'cpufreq package is absent'
for name in ('cpufreq.init', 'cpufreq.uci', 'xg2010g-cpu-policy'):
    shutil.copyfile(repo / 'CPU/runtime' / name, pkg / 'files' / name)
    (pkg / 'files' / name).chmod(0o755)
make = pkg / 'Makefile'
text = re.sub(r'^PKG_RELEASE:=.*$', 'PKG_RELEASE:=3', make.read_text(), flags=re.M)
if '$(1)/usr/libexec/xg2010g-cpu-policy' not in text:
    marker = '\t$(INSTALL_BIN) $(CURDIR)/files/cpufreq.init $(1)/etc/init.d/'
    assert marker in text, 'cpufreq install recipe changed'
    text = text.replace(marker, marker + '\n\t$(INSTALL_DIR) $(1)/usr/libexec\n\t$(INSTALL_BIN) $(CURDIR)/files/xg2010g-cpu-policy $(1)/usr/libexec/xg2010g-cpu-policy')
make.write_text(text)
(root / 'files/etc').mkdir(parents=True, exist_ok=True)
shutil.copyfile(repo / 'CPU-BOOST-SOURCE.json', root / 'files/etc/xg2010g-cpu-boost-source.json')
print('Installed XG2010G 500–1400MHz BL31-compatible kernel PLL boost and shared CPU policy service')
