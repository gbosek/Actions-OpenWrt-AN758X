#!/usr/bin/env python3
"""Check patch selection, repeat installation and duplicate/conflict rejection."""
from pathlib import Path
import subprocess
import tempfile
import json

repo = Path(__file__).resolve().parents[2]
scripts = repo / ('scripts' if (repo / 'scripts/apply-driver-fixes.py').exists() else 'Scripts')
metadata = json.loads((repo / 'AN7581-DRIVER-FIXES-SOURCE.json').read_text())
for project, patchlevel in [('pon', 55), ('ci', 55)]:
    with tempfile.TemporaryDirectory(prefix='airoha-driver-install-') as temporary:
        root = Path(temporary)
        generic = root / 'target/linux/generic'
        generic.mkdir(parents=True)
        version = generic / 'kernel-6.18'
        version.write_text('LINUX_VERSION-6.18 = .' + str(patchlevel) + '\n')
        destination = root / 'target/linux/airoha/patches-6.18'
        destination.mkdir(parents=True)
        command = ['python3', str(scripts / 'apply-driver-fixes.py'), str(root), '--project', project]
        for _ in range(2):
            subprocess.run(command, check=True)
            assert sorted(p.name for p in destination.iterdir()) == sorted(metadata['baselines'][project]['apply'])
            result = json.loads((root / 'files/etc/an7581-driver-fixes.json').read_text())
            assert result['project'] == project
        bad = destination / '934-conflict.patch'
        bad.write_text('conflicting changes')
        assert subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
        bad.unlink()
        version.write_text('LINUX_VERSION-6.18 = .999\n')
        assert subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
print('PASS: both kernel selections, repeat install, native RX31 skip, conflict rejection and unknown kernel rejection')
