#!/usr/bin/env python3
"""Install XG2010G boot fixes without touching mount entries or clock policy."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def install(root):
    repo = Path(__file__).resolve().parents[1]
    version = (root / 'target/linux/generic/kernel-6.18').read_text()
    assert re.search(r'^LINUX_VERSION-6\.18\s*:?=\s*\.55\s*$', version, re.M), 'Unreviewed kernel'
    queue = root / 'target/linux/airoha/patches-6.18'
    assert queue.is_dir()
    patch = repo / 'kernel-patches/airoha/938-net-phy-an7581-optional-led-pinctrl.patch'
    for old in queue.glob('938-*.patch'):
        assert old.name == patch.name and old.read_bytes() == patch.read_bytes(), 'Conflicting PHY patch'
    shutil.copyfile(patch, queue / patch.name)
    # Populate the read-only image before preinit/extroot probing. A uci-defaults
    # hook runs too late. Never overwrite supplied mount/extroot configuration.
    fstab = root / 'files/etc/config/fstab'
    fstab.parent.mkdir(parents=True, exist_ok=True)
    if not fstab.exists():
        shutil.copyfile(repo / 'Boot/root/etc/config/fstab', fstab)
        fstab.chmod(0o644)
    config = root / '.config'
    if config.exists():
        keys = ('CONFIG_BUSYBOX_CUSTOM', 'CONFIG_BUSYBOX_CONFIG_FEATURE_SYSLOG_INFO')
        lines = [line for line in config.read_text().splitlines()
                 if not any(line.startswith(key + '=') or line == '# ' + key + ' is not set' for key in keys)]
        config.write_text('\n'.join(lines + [key + '=y' for key in keys]) + '\n')
    provenance = root / 'files/etc/xg2010g-boot-fixes.json'
    provenance.write_text(json.dumps({
        'phy_patch': patch.name,
        'phy_patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
        'fstab_in_rom': True,
        'busybox_syslog_info': True,
        'clock_jump_detection': 'retained; do not run missed cron jobs after large time steps',
        'hardware_boot_tested': False,
    }, indent=2) + '\n')
    print('XG2010G: optional PHY LED mux, ROM fstab, BusyBox INFO logs; clock jump detection retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    install(parser.parse_args().source.resolve())
