#!/usr/bin/env python3
"""Apply the reviewed stable 6.18.52 -> 6.18.54 patch rebase to PonWrt."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
repo = Path(__file__).resolve().parents[1]
patch = repo / 'source-patches/ponwrt-6.18.52-to-6.18.54.patch'
version = root / 'target/linux/generic/kernel-6.18'
expected = '9df30b02dd8102bbd0be52556288ef6889ddbe7f1ddb96fbf847d0becf3eacac'
text = version.read_text()
if re.search(r'^LINUX_VERSION-6\.18 = \.52$', text, re.M):
    subprocess.run(['git','apply','--check',str(patch)], cwd=root, check=True)
    subprocess.run(['git','apply',str(patch)], cwd=root, check=True)
else:
    assert re.search(r'^LINUX_VERSION-6\.18 = \.54$', text, re.M), 'Unexpected kernel baseline'
    subprocess.run(['git','apply','--reverse','--check',str(patch)], cwd=root, check=True)
text = version.read_text()
assert f'LINUX_KERNEL_HASH-6.18.54 = {expected}' in text
out = root / 'files/etc/kernel-stable-backport.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'kernel':'6.18.54', 'tarball_sha256':expected,
    'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),
    'stable_commits':['411a8112dd1211b47469fd99dc9c0d25560f5b1c',
                      '142619bac5ba56d5c8adbb80b6a65095057e0a65'],
    'scope':'generic and airoha, preserving PonWrt feed/application baseline'}, indent=2)+'\n')
print('PonWrt stable kernel 6.18.54 and matching generic/Airoha patch rebases installed')
