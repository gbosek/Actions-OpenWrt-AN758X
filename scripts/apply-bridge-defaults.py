#!/usr/bin/env python3
"""Align the unfiltered XG2010G LAN default with the guarded L2 fallback."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAYLOAD = REPO / 'Offload/bridge-defaults'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def apply(root):
    meta = json.loads((PAYLOAD / 'SOURCE.json').read_text())
    fw = root / 'package/network/config/firewall4'
    assert 'b6e5157527d361f99ad52eaa6da273cb0f2dfd59' in (fw / 'Makefile').read_text(), 'Unreviewed fw4 version'
    original = fw / 'patches/001-add-bridge-flowtable-support.patch'
    assert sha(original.read_bytes()) == meta['original_bridge_patch_sha256'], 'Unreviewed bridge generator'
    patch = PAYLOAD / meta['package_patch']
    assert sha(patch.read_bytes()) == meta['package_patch_sha256'], 'Bridge-default patch changed'
    dest = fw / 'patches' / patch.name
    assert not dest.exists() or dest.read_bytes() == patch.read_bytes(), 'Conflicting fw4 default patch'
    # Validate every input before writing any source file.
    mk = root / 'package/kernel/linux/modules/netfilter.mk'
    text = mk.read_text()
    match = re.search(r'^define KernelPackage/br-netfilter\n.*?^endef$', text, re.M | re.S)
    assert match, 'br-netfilter package absent'
    before = match[0]
    old = '  AUTOLOAD:=$(call AutoProbe,br_netfilter)'
    new = '  # XG2010G: explicit bridge policy demand-loads br_netfilter.'
    assert before.count(old) == 1 or before.count(new) == 1, 'Unexpected bridge autoload definition'
    after = before.replace(old, new)
    sysctl = root / 'package/base-files/files/etc/init.d/sysctl'
    sys_text = sysctl.read_text()
    needle = 'start() {\n\tapply_defaults'
    replacement = 'start() {\n\t/usr/libexec/xg2010g-bridge-netfilter || logger -t xg2010g-bridge "Fallback remains closed: bridge policy setup failed"\n\tapply_defaults'
    assert sys_text.count(needle) == 1 or sys_text.count(replacement) == 1, 'Unexpected sysctl startup'
    default = root / 'package/kernel/linux/files/sysctl-br-netfilter.conf'
    assert sha(default.read_bytes()) == meta['packaged_bridge_sysctl_sha256'], 'Unreviewed default bridge sysctls'
    helper = PAYLOAD / 'xg2010g-bridge-netfilter'
    assert sha(helper.read_bytes()) == meta['helper_sha256'], 'Bridge request helper changed'
    shutil.copyfile(patch, dest)
    mk.write_text(text[:match.start()] + after + text[match.end():])
    sysctl.write_text(sys_text.replace(needle, replacement))
    target = root / 'files/usr/libexec/xg2010g-bridge-netfilter'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(helper, target)
    target.chmod(0o755)
    target = root / 'files/etc/airoha-bridge-defaults.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(meta, indent=2) + '\n')
    print('Bridge flowtable opt-in; br_netfilter demand-load; inet/custom policy and 949-952 guards retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source.resolve())
