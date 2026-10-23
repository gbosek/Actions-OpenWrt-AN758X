#!/usr/bin/env python3
"""Install the complete pinned, guarded PPE fallback patch set once."""
import argparse, hashlib, json, re, shutil
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__); p.add_argument('source', type=Path)
root = p.parse_args().source.resolve()
repo = Path(__file__).resolve().parents[1]
meta = json.loads((repo/'Offload/SOURCE.json').read_text())
assert re.search(r'^LINUX_VERSION-6\.18\s*:?=\s*\.55$', (root/'target/linux/generic/kernel-6.18').read_text(), re.M), 'Unreviewed kernel baseline'
queue = root/'target/linux/airoha/patches-6.18'
assert queue.is_dir(), 'Airoha patch queue missing'
for prefix in ('930-', '931-', '932-', '933-'):
    assert len(list(queue.glob(prefix+'*.patch'))) == 1, 'Missing retained native-L2B/reliability prerequisite: '+prefix
for pattern in ('9990-*', '9993-*', '9994-*'):
    assert not list(queue.glob(pattern)), 'Duplicate upstream fallback implementation: '+pattern
for patch in meta['patches']:
    src = repo/'Offload/patches'/patch['file']
    assert hashlib.sha256(src.read_bytes()).hexdigest() == patch['sha256'], 'Patch hash mismatch: '+src.name
    matches = list(queue.glob(src.name[:3]+'-*.patch'))
    assert not matches or (len(matches)==1 and matches[0].name==src.name and matches[0].read_bytes()==src.read_bytes()), 'Conflicting patch prefix: '+src.name
    shutil.copyfile(src, queue/src.name)
dest = root/'files/etc/airoha-offload-source.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n')
print('Installed guarded naoki PPE fallback, VLAN path API and hardware flowtable lifecycle')
