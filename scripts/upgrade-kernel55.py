#!/usr/bin/env python3
"""Upgrade pinned XG2010G kernel sources with the reviewed stable patch rebase."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('--project',choices=('pon','ci'),required=True)
a=p.parse_args();root=a.source.resolve();repo=Path(__file__).resolve().parents[1]
version=root/'target/linux/generic/kernel-6.18'
patch=repo/'source-patches'/(a.project+'-6.18.54-to-6.18.55.patch')
expected='f410638061a165c12f42ab871d2f3fcd525515359b5faeee80969cff84524df9'
text=version.read_text()
if not re.search(r'^LINUX_VERSION-6\.18 = \.55$',text,re.M):
    if a.project=='pon':
        subprocess.run([sys.executable,str(Path(__file__).with_name('upgrade-kernel54.py')),str(root)],check=True)
    text=version.read_text()
    assert re.search(r'^LINUX_VERSION-6\.18 = \.54$',text,re.M),'Unexpected kernel baseline'
    assert 'LINUX_KERNEL_HASH-6.18.54 = 9df30b02dd8102bbd0be52556288ef6889ddbe7f1ddb96fbf847d0becf3eacac' in text
    subprocess.run(['git','apply','--check',str(patch)],cwd=root,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=root,check=True)
else:
    subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=root,check=True)
assert 'LINUX_KERNEL_HASH-6.18.55 = '+expected in version.read_text()
if a.project=='pon':
    bbr=root/'target/linux/generic/hack-6.18/951-net-tcp-bbr3-support.patch'
    new=repo/'source-patches/951-net-tcp-bbr3-support-6.18.55.patch'
    if new.exists():
        old=repo/'source-patches/951-net-tcp-bbr3-support-6.18.54.patch'
        assert bbr.read_bytes() in (old.read_bytes(),new.read_bytes()),'Unexpected BBRv3 revision'
        bbr.write_bytes(new.read_bytes())
out=root/'files/etc/kernel-stable-backport.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(dict(kernel='6.18.55',project=a.project,tarball_sha256=expected,
    patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
    stable_commit='db9616b9af0cedb42c39bd73e60b2809be35fdd9',
    native_fixes=['935 NPU watchdog cleanup','936 RX31 IRQ'],
    scope='Stable kernel and generic/Airoha patch rebases; existing packages and settings retained'),indent=2)+'\n')
print(a.project+': Linux 6.18.55 and matching stable patch rebases installed')
