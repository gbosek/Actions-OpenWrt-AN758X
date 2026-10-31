#!/usr/bin/env python3
"""Apply the exact reviewed 6.18.55 -> 6.18.60 final-source migration."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def install(root):
    repo=Path(__file__).resolve().parents[1]
    meta=json.loads((repo/'Kernel60/SOURCE.json').read_text())
    patch=repo/'source-patches/pon-6.18.55-to-6.18.60.patch'
    assert digest(patch)==meta['upgrade_patch_sha256'],'Unreviewed upgrade delta'
    before=all(digest(root/r['path'])==r['before_sha256'] for r in meta['files'])
    after=all(digest(root/r['path'])==r['after_sha256'] for r in meta['files'])
    assert before or after,'Source differs from both exact reviewed migration states'
    subprocess.run(['git','apply','--whitespace=nowarn','--check',*(['--reverse'] if after else []),str(patch)],cwd=root,check=True)
    if before:subprocess.run(['git','apply','--whitespace=nowarn',str(patch)],cwd=root,check=True)
    assert all(digest(root/r['path'])==r['after_sha256'] for r in meta['files'])
    dest=root/'files/etc';dest.mkdir(parents=True,exist_ok=True)
    (dest/'kernel-stable-backport.json').write_text(json.dumps({
        'kernel':meta['kernel'],'project':'pon','tarball_sha256':meta['tarball_sha256'],
        'patch_sha256':meta['upgrade_patch_sha256'],'parent_kernel':meta['parent_kernel'],
        'native_fixes':meta['native_stable_do_not_duplicate'],
        'scope':'Reviewed stable upgrade and selective package fixes; hardware not tested'},indent=2)+'\n')
    (dest/'xg2010g-kernel60-source.json').write_text(json.dumps(meta,indent=2)+'\n')
    for name,target in [('Offload/SOURCE.json','airoha-offload-source.json'),('Upstream/SOURCE.json','xg2010g-upstream-source.json')]:
        (dest/target).write_bytes((repo/name).read_bytes())
    print('Linux 6.18.60 exact migration verified; native stable fixes not duplicated')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    install(p.parse_args().source.resolve())
