#!/usr/bin/env python3
"""Refresh the full October 18 build without replacing its functional baseline."""
from pathlib import Path
import argparse,json,re,shutil,subprocess,hashlib
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--phase',choices=['feeds','finish','check'],required=True);a=p.parse_args();S=a.source.resolve()
meta=json.loads((P/'source.json').read_text())
def package_symbols():
 # Manifest names include ABI suffixes; Kconfig symbols do not.
 result={}
 for block in (S/'tmp/.packageinfo').read_text().split('\n\n'):
  name=re.search(r'^Package: (.+)$',block,re.M)
  if not name:continue
  name=name[1];abi=re.search(r'^ABI-Version: (.+)$',block,re.M)
  result[name]=name
  if abi:result[name+abi[1]]=name
 return result
if a.phase=='feeds':
 f=S/'feeds.conf.default';t=f.read_text()
 for n,row in json.loads((P/'feed-pins.json').read_text())['feeds'].items():
  if n=='pon_userspace':continue # Keep the full baseline's reviewed ONU feed.
  t,count=re.subn(r'^src-git\s+'+re.escape(n)+r'\s+.*$','src-git '+n+' '+row['url']+'^'+row['commit'],t,flags=re.M);assert count==1,n
 f.write_text(t)
elif a.phase=='finish':
 for src in (P/'packages').iterdir():
  target=S/'package/custom'/src.name
  assert target.resolve().is_relative_to(S/'package/custom')
  if target.exists():shutil.rmtree(target)
  shutil.copytree(src,target)
  make=target/'Makefile';t=make.read_text().replace('include ../../luci.mk','include $(TOPDIR)/feeds/luci/luci.mk');make.write_text(t)
  for f in (target/'root').rglob('*'):
   if f.is_file() and (f.read_bytes().startswith(b'#!/') or 'libexec' in f.parts):f.chmod(0o755)
 # Avoid indexing both the old feed theme and the new pinned theme.
 for name in ['luci-theme-argon','luci-app-argon-config']:
  link=S/'package/feeds/luci'/name
  if link.is_symlink():link.unlink()
 # Preserve the requested raw PPE fields while updating the rest upstream.
 f=S/'package/custom/luci-app-airoha-npu/htdocs/luci-static/resources/view/airoha_npu/status.js';t=f.read_text()
 t=t.replace("if (eth === '00:00:00:00:00:00->00:00:00:00:00:00') eth = '-';",'// Preserve raw Ethernet values.')
 for k in ['packets','bytes']:t=t.replace(f"e.{k} === null || e.{k} === undefined ? 'N/A' : String(e.{k})",f"e.{k} === null || e.{k} === undefined ? '-' : String(e.{k})")
 f.write_text(t)
 shutil.copytree(P/'root',S/'files',dirs_exist_ok=True)
 # The current router explicitly runs MWAN4. Keep its current boot policy,
 # rather than reinstating the October image's "default off" migration.
 (S/'files/etc/uci-defaults/99-xg2010g-mwan4-default-off').unlink(missing_ok=True)
 for f in (P/'root').rglob('*'):
  if f.is_file() and f.read_bytes().startswith(b'#!/'): (S/'files'/f.relative_to(P/'root')).chmod(0o755)
 # Carry all baseline package selections, not the earlier minimal selection.
 manifests=(P/'baseline.manifest').read_text()+(P/'current-installed.manifest').read_text()
 names=sorted({line.split(' - ',1)[0] for line in manifests.splitlines() if ' - ' in line})
 # Argon 3.1 includes the settings previously supplied by argon-config.
 omit={'kernel','luci-app-argon-config'}
 f=S/'.config';t=f.read_text()
 t=re.sub(r'^CONFIG_TARGET_(?:DEVICE_)?airoha_an7581_DEVICE_(?!gemtek_xg2010g(?:=|\b))[^\n]*\n?','',t,flags=re.M)
 symbols=package_symbols()
 for manifest_name in names:
  n=symbols.get(manifest_name,manifest_name)
  key='CONFIG_PACKAGE_'+n;t=re.sub(r'^(?:'+re.escape(key)+r'=.*|# '+re.escape(key)+r' is not set)\n?','',t,flags=re.M)
  if n not in omit:t+=key+'=y\n'
 t+='\n# CONFIG_PACKAGE_luci-app-argon-config is not set\nCONFIG_PACKAGE_wget-ssl=y\nCONFIG_PACKAGE_coreutils=y\nCONFIG_PACKAGE_coreutils-timeout=y\nCONFIG_PACKAGE_ucode-mod-math=y\n'
 for key in ['IMAGEOPT','VERSIONOPT','VERSION_NUMBER','VERSION_DIST']:
  t=re.sub(r'^(?:CONFIG_'+key+r'=.*|# CONFIG_'+key+r' is not set)\n?','',t,flags=re.M)
 t+='CONFIG_IMAGEOPT=y\nCONFIG_VERSIONOPT=y\nCONFIG_VERSION_DIST="PonWrt"\nCONFIG_VERSION_NUMBER="2026.11.09-refresh3"\n'
 f.write_text(t)
 out=S/'files/etc/stable-refresh-source.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(meta,indent=2)+'\n')
 mwan_meta={k:v for k,v in meta['mwan4'].items() if k!='files'}
 (S/'files/etc/xg2010g-mwan4-source.json').write_text(json.dumps(mwan_meta,indent=2)+'\n')
 (S/'files/etc/airoha-build-source.json').write_text(json.dumps({'upstream':'naoki66/luci-app-airoha','commit':meta['airoha_commit'],'cpu_control':'upstream removed'},indent=2)+'\n')
 (S/'files/etc/pon-status-layout.json').write_text(json.dumps({'upstream':'naoki66/OpenWrt_ONU_CONFIG','commit':meta['pon_card_commit'],'version':'0.1.0-r13'},indent=2)+'\n')
elif a.phase=='check':
 cfg=(S/'.config').read_text();selected=set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=y$',cfg,re.M))
 # Hidden profile packages are built as modules, then included per device.
 if 'CONFIG_TARGET_PER_DEVICE_ROOTFS=y' in cfg:
  profile_packages=set(re.findall(r'^CONFIG_MODULE_DEFAULT_([^=]+)=y$',cfg,re.M))
  modules=set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=m$',cfg,re.M))
  selected.update(profile_packages & modules)
 symbols=package_symbols()
 manifests=(P/'baseline.manifest').read_text()+(P/'current-installed.manifest').read_text()
 baseline={symbols.get(line.split(' - ',1)[0],line.split(' - ',1)[0]) for line in manifests.splitlines() if ' - ' in line}-{'kernel','luci-app-argon-config'}
 assert not baseline-selected,'Unexpected missing baseline packages: '+str(sorted(baseline-selected))
 assert 'CONFIG_VERSION_NUMBER="2026.11.09-refresh3"' in cfg,'Dated version was not retained by Kconfig'
 info=(S/'tmp/.packageinfo').read_text()
 assert re.search(r'^Package: luci-i18n-mwan4-zh-cn\n(?:(?!Package:).)*?^Version: 1\.0\.0-r19$',info,re.M|re.S),'Vendored MWAN4 translation version is missing'
 assert 'LINUX_VERSION-6.18 = .55' in (S/'target/linux/generic/kernel-6.18').read_text()
 dts=(S/'target/linux/airoha/dts/an7581.dtsi').read_text();hz=[int(x) for x in re.findall(r'opp-hz\s*=\s*/bits/\s*64\s*<\s*(\d+)',dts)]
 assert hz and max(hz)==1200000000,hz
 assert not list((S/'target/linux/airoha/patches-6.18').glob('*overclock*'))
 for name in meta['rtl826x']['patches']:
  assert (S/'target/linux/airoha/patches-6.18'/name).read_bytes()==(P.parent/'kernel-patches/airoha'/name).read_bytes(),name
 patch_manifest=P/'kernel-patches.json'
 assert hashlib.sha256(patch_manifest.read_bytes()).hexdigest()==meta['kernel_patch_manifest_sha256']
 for row in json.loads(patch_manifest.read_text()):
  assert hashlib.sha256((S/row['path']).read_bytes()).hexdigest()==row['sha256'],'Kernel patch changed or missing: '+row['path']
 for rel in ['etc/firewall.lan-fakeip.nft','usr/sbin/xg-cn-split-setup','usr/bin/mwan4-rule-guard.sh','usr/share/nftables.d/ruleset-post/20-cn-split.nft']:
  assert (S/'files'/rel).read_bytes()==(P/'root'/rel).read_bytes(),rel
 f=S/'files/etc/uci-defaults/99-stable-refresh';t=f.read_text();assert 'omcproxy disable' not in t and 'ra-refresh' not in t
 print('PASS full baseline package set, native CPU <=1200MHz, effective live rules and kernel 6.18.55')
