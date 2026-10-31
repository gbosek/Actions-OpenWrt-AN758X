#!/usr/bin/env python3
"""Replay both generic headers and target queues strictly forward on official60."""
from pathlib import Path
import argparse,difflib,hashlib,json,shutil,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def apply(root,patch,log):
    result=subprocess.run(['patch','--forward','--batch','--fuzz=0','-p1','-i',str(patch)],cwd=root,text=True,capture_output=True)
    log.write(str(patch)+'\n'+result.stdout+result.stderr);log.flush()
    if result.returncode or 'Assuming -R' in result.stdout or 'with fuzz' in result.stdout:
        raise RuntimeError('Strict forward patch failed: '+str(patch)+'\n'+result.stdout+result.stderr)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--report',type=Path);p.add_argument('--work-dir',type=Path);p.add_argument('--scope',choices=['headers','firmware','both'],default='both')
    a=p.parse_args();S=a.source.resolve();m=json.loads((R/'Kernel60/SOURCE.json').read_text());archive=a.archive or S/'dl/linux-6.18.60.tar.xz';assert sha(archive)==m['tarball_sha256']
    report=a.report or S/'KERNEL60-PATCH-QUEUE-VERIFICATION.json';logpath=report.with_suffix('.log');report.parent.mkdir(parents=True,exist_ok=True)
    out={'kernel':'6.18.60','archive_sha256':sha(archive),'direction':'forward-only','fuzz':0,'scopes':{},'hardware_tested':False}
    with logpath.open('w') as log:
        # Exercise the same apply() on an already-native feature. Automatic -R
        # must fail the check and leave the source unchanged.
        with tempfile.TemporaryDirectory(prefix='native-patch-control-') as d:
            d=Path(d);source=d/'sample';source.write_text('native\nadded\n');before=sha(source)
            patch=d/'duplicate.patch';patch.write_text(''.join(difflib.unified_diff(['native\n'],['native\n','added\n'],fromfile='a/sample',tofile='b/sample')))
            try:apply(d,patch,log)
            except RuntimeError:pass
            else:raise AssertionError('Already-native patch was accepted')
            assert sha(source)==before;out['negative_control']='native duplicate rejected, no reversal'
        for scope in (['headers','firmware'] if a.scope=='both' else [a.scope]):
            with tempfile.TemporaryDirectory(prefix='kernel60-'+scope+'-',dir=a.work_dir) as d:
                d=Path(d);subprocess.run(['tar','-xf',str(archive),'-C',str(d)],check=True);K=d/'linux-6.18.60'
                for parent in ['generic']+(['airoha'] if scope=='firmware' else []):
                    for folder in ['files','files-6.18']:
                        src=S/'target/linux'/parent/folder
                        if src.is_dir():shutil.copytree(src,K,dirs_exist_ok=True)
                patches=[r for r in m['patch_queue'] if scope=='firmware' or not r['path'].startswith('target/linux/airoha/')]
                for r in patches:
                    path=S/r['path'];assert sha(path)==r['sha256'];apply(K,path,log)
                option=(K/'drivers/usb/serial/option.c').read_text()
                assert option.count('#define QUECTEL_PRODUCT_EG060W')==1
                assert option.count('USB_DEVICE_AND_INTERFACE_INFO(QUECTEL_VENDOR_ID, QUECTEL_PRODUCT_EG060W,')==1
                checked={}
                if scope=='firmware':
                    expected=json.loads((R/'Offload/SOURCE.json').read_text())['expected_prepared_sources']|m['prepared_sources']
                    for n,h in expected.items():assert sha(K/n)==h,n;checked[n]=h
                else:
                    # This is the failed toolchain's next real operation, using
                    # host build tools only; no target compiler is needed yet.
                    result=subprocess.run(['make','-s','-C',str(K),'ARCH=arm64','INSTALL_HDR_PATH='+str(d/'headers'),'headers_install'],stdout=log,stderr=subprocess.STDOUT)
                    log.flush();assert result.returncode==0,'ARM64 UAPI headers_install failed'
                    assert (d/'headers/include/asm/unistd.h').is_file()
                out['scopes'][scope]={'patches':len(patches),'native_eg060w_retained':True,'prepared_sources':checked}
                if scope=='headers':out['scopes'][scope]['arm64_uapi_headers_install']='passed'
                print('PASS',scope,len(patches),'strict-forward zero-fuzz patches',flush=True)
    out['status']='passed';report.write_text(json.dumps(out,indent=2)+'\n')
    print('PASS strict headers + target patch queues and native duplicate negative control')

if __name__=='__main__':main()
