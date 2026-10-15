#!/usr/bin/env python3
"""Install exact upstream fixes once, respecting the two pinned kernel bases."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def install(root, project):
    repo = Path(__file__).resolve().parents[1]
    metadata = json.loads((repo / 'AN7581-DRIVER-FIXES-SOURCE.json').read_text())
    baseline = metadata['baselines'][project]
    details = (root / 'target/linux/generic/kernel-6.18').read_text()
    match = re.search(r'^LINUX_VERSION-6\.18\s*:?=\s*\.(\d+)\s*$', details, re.M)
    assert match and '6.18.' + match[1] == baseline['kernel'], 'Unreviewed kernel base'
    destination = root / 'target/linux/airoha/patches-6.18'
    assert destination.is_dir(), 'Airoha patch directory missing'
    for patch in metadata['patches']:
        origin = repo / 'kernel-patches/airoha' / patch['file']
        assert hashlib.sha256(origin.read_bytes()).hexdigest() == patch['sha256'], 'Upstream patch hash mismatch'
        existing = list(destination.glob(patch['file'][:3] + '-*.patch'))
        if patch['file'] not in baseline['apply']:
            assert not existing, 'RX31 is already fixed in this kernel base; duplicate patch rejected'
            continue
        for path in existing:
            assert path.name == patch['file'] and path.read_bytes() == origin.read_bytes(), 'Conflicting patch: ' + str(path)
        shutil.copyfile(origin, destination / patch['file'])
    output = dict(metadata, project=project, selected_baseline=baseline)
    path = root / 'files/etc/an7581-driver-fixes.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(project + ': upstream driver fixes installed; native RX31 fix retained where present')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--project', required=True, choices=['pon', 'ci'])
    args = parser.parse_args()
    install(args.source, args.project)
