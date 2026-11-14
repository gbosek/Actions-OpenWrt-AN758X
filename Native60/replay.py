#!/usr/bin/env python3
from pathlib import Path
import subprocess,shutil,json,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('work',type=Path);p.add_argument('--archive',type=Path);a=p.parse_args();S=a.source.resolve();D=a.work.resolve();P=Path(__file__).resolve().parent
assert not D.exists(),'Use a fresh replay directory'
D.mkdir(parents=True);archive=a.archive or S/'dl/linux-6.18.60.tar.xz'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(archive)=='3c2f44ef6acc021a7ad444d9a2e6ec1ef488ff09368793d0004a6080f69d621e'
subprocess.run(['tar','-xf',str(archive),'-C',str(D)],check=True);K=D/'linux-6.18.60';rows=[]
for parent in ['generic','airoha']:
 for folder in ['files','files-6.18']:
  f=S/'target/linux'/parent/folder
  if f.is_dir():shutil.copytree(f,K,dirs_exist_ok=True)
with (D/'replay.log').open('w') as log:
 for folder in ['generic/backport-6.18','generic/pending-6.18','generic/hack-6.18','airoha/patches-6.18']:
  if folder=='airoha/patches-6.18':
   subprocess.run(['make','-s','ARCH=arm64','INSTALL_HDR_PATH='+str(D/'headers'),'headers_install'],cwd=K,check=True,stdout=log,stderr=subprocess.STDOUT)
  for f in sorted((S/'target/linux'/folder).glob('*.patch')):
   r=subprocess.run(['patch','--forward','--batch','--fuzz=0','-p1','-i',str(f)],cwd=K,text=True,capture_output=True)
   log.write(str(f)+'\n'+r.stdout+r.stderr);log.flush()
   assert r.returncode==0 and 'Assuming -R' not in r.stdout,(f.name,r.stdout,r.stderr)
   rows.append({'path':str(f.relative_to(S)),'sha256':digest(f)})
keys=['drivers/net/ethernet/airoha/airoha_eth.c','drivers/net/ethernet/airoha/airoha_ppe.c','drivers/net/ethernet/airoha/airoha_npu.c','drivers/net/phy/realtek/realtek_main.c','drivers/thermal/airoha_thermal.c','net/netfilter/nft_flow_offload.c','net/netfilter/nf_flow_table_core.c','net/bridge/br.c']
hashes={n:digest(K/n) for n in keys}
for name,obj in [('patch-manifest.json',rows),('prepared-sources.json',hashes)]:
 f=P/name
 if f.exists():assert json.loads(f.read_text())==obj,'Prepared source or patch input drift: '+name
 else:f.write_text(json.dumps(obj,indent=2)+'\n')
(D/'verification.json').write_text(json.dumps({'status':'passed','kernel':'6.18.60','patches':len(rows),'strict_forward':True,'fuzz':0,'sources':hashes},indent=2)+'\n')
print('PASS',len(rows),'strict-forward zero-fuzz patches and exact prepared source hashes')
