#!/usr/bin/env python3
"""Exercise exact installer, idempotence, drift and duplicate rejection."""
from pathlib import Path
import json,subprocess,tempfile,sys,hashlib
R=Path(__file__).resolve().parents[1];meta=json.loads((R/'Kernel60/SOURCE.json').read_text());patch=R/'source-patches/pon-6.18.55-to-6.18.60.patch'
assert len({r['path'] for r in meta['files']})==len(meta['files'])
assert hashlib.sha256(patch.read_bytes()).hexdigest()==meta['upgrade_patch_sha256']
assert all(r['after_sha256'] and len(r['after_sha256'])==64 for r in meta['files'])
assert meta['kernel']=='6.18.60' and meta['parent_kernel']=='6.18.55'
assert len(list((R/'Kernel60/patches').glob('961-*.patch')))==1
if len(sys.argv)>1:
    source=Path(sys.argv[1]);import shutil
    with tempfile.TemporaryDirectory(prefix='kernel60-real-installer-') as d:
        root=Path(d)
        for r in meta['files']:
            dest=root/r['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/r['path'],dest)
        subprocess.run(['git','apply','--whitespace=nowarn','--reverse',str(patch)],cwd=root,check=True)
        command=[sys.executable,str(R/'scripts/upgrade-kernel60.py'),str(root)]
        subprocess.run(command,check=True);subprocess.run(command,check=True)
        for r in meta['files']:assert hashlib.sha256((root/r['path']).read_bytes()).hexdigest()==r['after_sha256']
        target=root/meta['files'][0]['path'];target.write_bytes(target.read_bytes()+b'\n/* unreviewed drift */\n')
        assert subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    print('PASS real complete-source installer: install, repeat, final hashes and drift rejection')
else:print('PASS migration inventory and patch identity; real source installer test requires source argument')
