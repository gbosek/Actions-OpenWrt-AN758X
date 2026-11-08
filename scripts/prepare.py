#!/usr/bin/env python3
"""Apply the user's minimal, pinned additions to pristine PonWrt."""
from pathlib import Path
import argparse,subprocess,shutil,json,re,hashlib,os
P=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--phase',choices=['base','packages','check'],required=True);a=p.parse_args();S=a.source.resolve()
meta=json.loads((P/'components.json').read_text())
def run(args,**kw):subprocess.run([str(x) for x in args],check=True,**kw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clone(name,row):
 d=P/'upstreams'/name
 g=['git','-c','safe.directory='+str(d),'-C',d]
 if not (d/'.git').exists():d.mkdir(parents=True,exist_ok=True);run(['git','init','-q',d])
 remote=subprocess.run([str(x) for x in g+['remote','get-url','origin']],text=True,capture_output=True)
 url='https://github.com/'+row['repository']+'.git'
 if remote.returncode:run(g+['remote','add','origin',url])
 else:assert remote.stdout.strip()==url
 head=subprocess.run([str(x) for x in g+['rev-parse','HEAD']],text=True,capture_output=True)
 if head.returncode or head.stdout.strip()!=row['commit']:
  run(g+['-c','http.version=HTTP/1.1','fetch','--depth=1','origin',row['commit']]);run(g+['checkout','--detach','FETCH_HEAD'])
 assert subprocess.check_output([str(x) for x in g+['rev-parse','HEAD']],text=True).strip()==row['commit']
 return d
if a.phase=='base':
 assert 'LINUX_VERSION-6.18 = .52' in (S/'target/linux/generic/kernel-6.18').read_text()
 original=[{'path':str(x.relative_to(S)),'sha256':sha(x)} for root in ['generic/backport-6.18','generic/pending-6.18','generic/hack-6.18','airoha/patches-6.18'] for x in sorted((S/'target/linux'/root).glob('*.patch'))]
 (P/'native-patch-queue.json').write_text(json.dumps(original,indent=2)+'\n')
 run(['python3',P/'scripts/upgrade-kernel55.py',S,'--project','pon'])
 dest=S/'target/linux/airoha/patches-6.18/939-net-phy-realtek-harden-rtl826x-reset.patch'
 assert not dest.exists();shutil.copyfile(P/'patches/939-net-phy-realtek-harden-rtl826x-reset.patch',dest)
 pins=json.loads((P/'feeds.json').read_text())
 text=(S/'feeds.conf.default').read_text()
 for name,row in pins['feeds'].items():
  text,n=re.subn(r'^src-git\s+'+re.escape(name)+r'\s+\S+.*$', 'src-git '+name+' '+row['url']+'^'+row['commit'],text,flags=re.M);assert n==1,name
 (S/'feeds.conf.default').write_text(text)
 print('PASS pristine base + necessary 6.18.55 adaptation + one RTL826x patch; feeds fixed to compatibility snapshot')
elif a.phase=='packages':
 custom=S/'package/custom';custom.mkdir(exist_ok=True)
 upstreams={name:clone(name,meta[name]) for name in ['airoha','pon_card','mwan4','luci_mwan4','argon']}
 for name,d in upstreams.items():
  src=d/meta[name]['package'] if 'package' in meta[name] else d
  target=custom/(meta[name].get('directory') or meta[name].get('package') or ('luci-app-mwan4' if name=='luci_mwan4' else 'mwan4'))
  assert not target.exists(),target
  shutil.copytree(src,target,ignore=shutil.ignore_patterns('.git','AGENTS.md','.workbuddy','__pycache__'))
 frontend=custom/'luci-app-mwan4/Makefile'
 text=frontend.read_text();assert 'include ../../luci.mk' in text
 frontend.write_text(text.replace('include ../../luci.mk','include $(TOPDIR)/feeds/luci/luci.mk',1))
 view=custom/'luci-app-airoha-npu/htdocs/luci-static/resources/view/airoha_npu/status.js'
 text=view.read_text();old="\t\tif (eth === '00:00:00:00:00:00->00:00:00:00:00:00') eth = '-';"
 assert text.count(old)==1;text=text.replace(old,'\t\t// Preserve raw zero Ethernet fields, as requested.')
 for key in ['packets','bytes']:
  old=f"e.{key} === null || e.{key} === undefined ? 'N/A' : String(e.{key})"
  assert text.count(old)==1;text=text.replace(old,f"e.{key} === null || e.{key} === undefined ? '-' : String(e.{key})")
 view.write_text(text)
 # Only this status-RPC compatibility adjustment is needed by the pinned LuCI.
 status=custom/'luci-app-mwan4/htdocs/luci-static/resources/view/mwan4/network/overview.js'
 text=status.read_text();old="const callStatus = rpc.declare({\n\tobject: 'mwan4',";assert text.count(old)==1
 status.write_text(text.replace(old,"const callStatus = rpc.declare({\n\tnobatch: true,\n\tobject: 'mwan4',",1))
 for f in (custom/'luci-app-airoha-npu/root').rglob('*'):
  if f.is_file() and (f.read_bytes().startswith(b'#!/bin/sh') or '/usr/libexec/' in str(f)):f.chmod(0o755)
 shutil.copytree(P/'files',S/'files',dirs_exist_ok=True)
 (S/'files/etc/uci-defaults/99-xg2010g-baseline').chmod(0o755)
 # A minimal package selection; board DTS/config and required Ethernet PHY/PCS remain native.
 cfg=(P/'xg2010g.config').read_text();(S/'.config').write_text(cfg)
 overlay=S/'files/etc';overlay.mkdir(parents=True,exist_ok=True)
 (overlay/'clean-build-source.json').write_text(json.dumps(meta,indent=2)+'\n')
 (overlay/'firmware-feed-pins.json').write_text((P/'feeds.json').read_text())
 print('PASS only four requested package repositories + raw-field UI adjustment installed')
elif a.phase=='check':
 text=(S/'.config').read_text()
 required=['TARGET_airoha_an7581_DEVICE_gemtek_xg2010g','PACKAGE_luci-app-airoha-npu','PACKAGE_luci-app-pon-status','PACKAGE_luci-app-mwan4','PACKAGE_mwan4','PACKAGE_airoha-pond','PACKAGE_airoha-ponctl','PACKAGE_kmod-airoha-xpon','PACKAGE_kmod-phy-realtek','KERNEL_DEVMEM']
 for key in required:assert 'CONFIG_'+key+'=y' in text,key
 assert 'CONFIG_PACKAGE_luci-theme-argon=y' in text
 # Native AN7581 CPU operating points stop at 1200 MHz; no PLL/turbo patch.
 dts=(S/'target/linux/airoha/dts/an7581.dtsi').read_text()
 frequencies=[int(x) for x in re.findall(r'opp-hz\s*=\s*/bits/\s*64\s*<\s*(\d+)\s*>',dts)]
 assert frequencies and max(frequencies)==1200000000,frequencies
 backend=(S/'package/custom/luci-app-airoha-npu/root/usr/libexec/rpcd/luci.airoha_npu').read_text()
 assert not re.search(r'^\s*(setGovernor|setMaxFreq|setCpuSettings)\)',backend,re.M)
 for key in ['PACKAGE_kmod-mac80211','PACKAGE_wpad-basic-mbedtls','PACKAGE_luci-app-mwan3','PACKAGE_mwan3']:
  assert 'CONFIG_'+key+'=y' not in text,key
 assert 'LINUX_VERSION-6.18 = .55' in (S/'target/linux/generic/kernel-6.18').read_text()
 native={row['path'] for row in json.loads((P/'native-patch-queue.json').read_text())}
 actual={str(f.relative_to(S)) for root in ['generic/backport-6.18','generic/pending-6.18','generic/hack-6.18','airoha/patches-6.18'] for f in (S/'target/linux'/root).glob('*.patch')}
 added=actual-native
 assert added=={'target/linux/airoha/patches-6.18/939-net-phy-realtek-harden-rtl826x-reset.patch'},added
 assert not (S/'files/usr/sbin/xg-dns-log-limit').exists()
 (P/'prepared-source.json').write_text(json.dumps({'added_kernel_patches':sorted(added),'kernel':'6.18.55','previous_local_feature_patches_inherited':False,'raw_ui_sha256':sha(S/'package/custom/luci-app-airoha-npu/htdocs/luci-static/resources/view/airoha_npu/status.js')},indent=2)+'\n')
 print('PASS selected packages, kernel .55, no inherited local feature patch additions')
