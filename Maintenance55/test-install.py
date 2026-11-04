#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[1];m=json.loads((R/'Maintenance55/SOURCE.json').read_text())
patch=R/'source-patches/pon-6.18.55-maintenance-20261104.patch'
assert hashlib.sha256(patch.read_bytes()).hexdigest()==m['maintenance_patch_sha256']
assert m['kernel']=='6.18.55'
assert len({x['path'] for x in m['files']})==len(m['files'])
if len(sys.argv)>1:
    S=Path(sys.argv[1])
    with tempfile.TemporaryDirectory(prefix='maintenance55-install-') as d:
        d=Path(d)
        for x in m['files']:
            p=d/x['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/x['path'],p)
        n='target/linux/generic/kernel-6.18';p=d/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/n,p)
        subprocess.run(['git','apply','--reverse','--whitespace=nowarn',str(patch)],cwd=d,check=True)
        cmd=[sys.executable,str(R/'scripts/apply-maintenance55.py'),str(d)]
        subprocess.run(cmd,check=True);subprocess.run(cmd,check=True)
        for x in m['files']:assert hashlib.sha256((d/x['path']).read_bytes()).hexdigest()==x['after_sha256']
        p=d/m['files'][0]['path'];p.write_bytes(p.read_bytes()+b'\n/* drift */\n')
        assert subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    print('PASS actual .55 installer, repeat execution, final hashes and drift rejection')
else:print('PASS .55 maintenance source inventory and delta hash')
