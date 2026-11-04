#!/usr/bin/env python3
"""Install the exact selected maintenance delta on the retained .55 baseline."""
from pathlib import Path
import argparse,hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def install(S):
    m=json.loads((R/'Maintenance55/SOURCE.json').read_text())
    patch=R/'source-patches/pon-6.18.55-maintenance-20261104.patch'
    assert sha(patch)==m['maintenance_patch_sha256'],'Maintenance delta changed'
    before=all(sha(S/x['path'])==x['before_sha256'] for x in m['files'])
    after=all(sha(S/x['path'])==x['after_sha256'] for x in m['files'])
    assert before or after,'Source differs from exact reviewed .55 maintenance states'
    subprocess.run(['git','apply','--whitespace=nowarn','--check',*(['--reverse'] if after else []),str(patch)],cwd=S,check=True)
    if before:subprocess.run(['git','apply','--whitespace=nowarn',str(patch)],cwd=S,check=True)
    assert all(sha(S/x['path'])==x['after_sha256'] for x in m['files'])
    assert 'LINUX_VERSION-6.18 = .55' in (S/'target/linux/generic/kernel-6.18').read_text()
    dest=S/'files/etc';dest.mkdir(parents=True,exist_ok=True)
    (dest/'xg2010g-maintenance55-source.json').write_text(json.dumps(m,indent=2)+'\n')
    for n,target in [('Offload/SOURCE.json','airoha-offload-source.json'),('Upstream/SOURCE.json','xg2010g-upstream-source.json')]:
        (dest/target).write_bytes((R/n).read_bytes())
    print('PASS exact Linux6.18.55 maintenance applied; no kernel version migration')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    install(p.parse_args().source.resolve())
