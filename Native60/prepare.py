#!/usr/bin/env python3
"""Exact full-baseline -> native CPU 6.18.60, with exclusive routing variants."""
from pathlib import Path
import argparse,json,hashlib,re,shutil,subprocess,os
P=Path(__file__).resolve().parent;R=P.parent
q=argparse.ArgumentParser();q.add_argument('source',type=Path);q.add_argument('--variant',choices=['mwan4','pbr'],required=True);q.add_argument('--check',action='store_true');a=q.parse_args();S=a.source.resolve()
meta=json.loads((P/'source.json').read_text())
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
def disable(t,n):return re.sub(r'^(?:CONFIG_PACKAGE_'+re.escape(n)+r'=.*|# CONFIG_PACKAGE_'+re.escape(n)+r' is not set)\n?','',t,flags=re.M)+'# CONFIG_PACKAGE_'+n+' is not set\n'
if not a.check:
 m=json.loads((R/'Kernel60/SOURCE.json').read_text());patch=R/'source-patches/pon-6.18.55-to-6.18.60.patch'
 assert sha(patch)==m['upgrade_patch_sha256']
 before=all(sha(S/r['path'])==r['before_sha256'] for r in m['files'])
 after=all(sha(S/r['path'])==r['after_sha256'] for r in m['files'])
 assert before or after,'Migration preimage differs'
 if before:
  subprocess.run(['git','apply','--check',str(patch)],cwd=S,check=True)
  subprocess.run(['git','apply',str(patch)],cwd=S,check=True)
 assert all(sha(S/r['path'])==r['after_sha256'] for r in m['files'])
 for f in (P/'kernel-patches').glob('*.patch'):shutil.copy2(f,S/'target/linux/airoha/patches-6.18'/f.name)
 app=S/'package/custom/luci-app-airoha-npu'
 rpc=app/'root/usr/libexec/rpcd/luci.airoha_npu';text=rpc.read_text()
 start=text.index('\t# NPU memory regions don\'t change after boot') if '\t# NPU memory regions don\'t change after boot' in text else text.index('\t# DT is authoritative')
 end=text.index('\t# Nothing about cpufreq',start)
 text=text[:start]+(P/'npu-memory-block.sh').read_text()+text[end:];rpc.write_text(text)
 helper=app/'root/usr/libexec/airoha-npu-memory';shutil.copy2(P/'airoha-npu-memory',helper);helper.chmod(0o755)
 make=app/'Makefile';make.write_text(make.read_text().replace('PKG_RELEASE:=9\n','PKG_RELEASE:=901\n'))
 # Remove inherited personal policy overlays from both variants. Keep the
 # ordinary board, DHCP, CPU, PON and firewall defaults from the full image.
 for f in list((S/'files').rglob('*')):
  if f.is_file() and (any(x in f.name for x in ['cn-split','cn_split','fakeip','mwan4-preset','mwan4-rule-guard']) or f.name in ['mwan4.user','99-stable-refresh','99-mwan4-guard','99-xg2010g-mwan4-default-off']):f.unlink()
 for rel in ['etc/config/mwan4','etc/xg2010g-mwan4-source.json','etc/stable-refresh-source.json']:
  (S/'files'/rel).unlink(missing_ok=True)
 packages=S/'package/custom'
 for n in ['pbr','luci-app-pbr','mwan3','luci-app-mwan3']:
  f=S/'package/feeds/packages'/n
  if f.is_symlink():f.unlink()
  f=S/'package/feeds/luci'/n
  if f.is_symlink():f.unlink()
 if a.variant=='pbr':
  for n in ['mwan4','luci-app-mwan4','luci-i18n-mwan4-zh-cn']:
   f=packages/n
   if f.exists():shutil.rmtree(f)
  for src in (P/'packages').iterdir():shutil.copytree(src,packages/src.name,dirs_exist_ok=True)
 for src in packages.iterdir():
  for f in src.rglob('*'):
   if f.is_file():
    data=f.read_bytes()
    if b'\0' not in data and b'\r\n' in data:
     try:data.decode('utf-8')
     except UnicodeDecodeError:pass
     else:f.write_bytes(data.replace(b'\r\n',b'\n'))
    if data.startswith(b'#!/'):f.chmod(0o755)
 # Both routing engines ship disabled with no enabled personal policies.
 if a.variant=='mwan4':
  cfg=packages/'mwan4/files/etc/config/mwan4';t=cfg.read_text();t=re.sub(r"option enabled '[01]'","option enabled '0'",t);cfg.write_text(t)
 init=S/'files/etc/uci-defaults/99-native60';init.parent.mkdir(parents=True,exist_ok=True)
 init.write_text("#!/bin/sh\nuci -q delete airoha_npu.@cpu[0]\nuci -q commit airoha_npu\nuci set cpufreq.cpufreq=cpufreq\nuci set cpufreq.cpufreq.governor0=ondemand\nuci set cpufreq.cpufreq.minfreq0=500000\nuci set cpufreq.cpufreq.maxfreq0=1200000\nuci commit cpufreq\nuci set luci.main.mediaurlbase='/luci-static/argon'\nuci commit luci\n/etc/init.d/"+a.variant+" disable\nexit 0\n");init.chmod(0o755)
 cfg=S/'.config';t=cfg.read_text()
 for n in ['mwan4','luci-app-mwan4','luci-i18n-mwan4-zh-cn','pbr','luci-app-pbr','luci-i18n-pbr-zh-cn','mwan3','luci-app-mwan3','vpn-policy-routing','luci-app-vpn-policy-routing']:t=disable(t,n)
 for n in (['mwan4','luci-app-mwan4','luci-i18n-mwan4-zh-cn'] if a.variant=='mwan4' else ['pbr','luci-app-pbr','luci-i18n-pbr-zh-cn']):t+='CONFIG_PACKAGE_'+n+'=y\n'
 t=re.sub(r'^CONFIG_VERSION_NUMBER=.*$', 'CONFIG_VERSION_NUMBER="2026.11.14-native60-'+a.variant+'"',t,flags=re.M);cfg.write_text(t)
 (S/'files/etc/native60-source.json').write_text(json.dumps(meta|{'variant':a.variant},indent=2)+'\n')
else:
 cfg=(S/'.config').read_text();selected=set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=y$',cfg,re.M))
 selected.update(set(re.findall(r'^CONFIG_MODULE_DEFAULT_([^=]+)=y$',cfg,re.M)) & set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=m$',cfg,re.M)))
 symbols={}
 for block in (S/'tmp/.packageinfo').read_text().split('\n\n'):
  n=re.search(r'^Package: (.+)$',block,re.M);abi=re.search(r'^ABI-Version: (.+)$',block,re.M)
  if n:symbols[n[1]]=n[1];symbols[n[1]+(abi[1] if abi else '')]=n[1]
 baseline={symbols.get(l.split(' - ',1)[0],l.split(' - ',1)[0]) for l in ((R/'StableRefresh/baseline.manifest').read_text()+(R/'StableRefresh/current-installed.manifest').read_text()).splitlines() if ' - ' in l}
 omit={'kernel','luci-app-argon-config'}
 if a.variant=='pbr':omit|={'mwan4','luci-app-mwan4','luci-i18n-mwan4-zh-cn'}
 assert not baseline-omit-selected,'Missing full-baseline packages '+str(sorted(baseline-omit-selected))
 wanted={'mwan4','luci-app-mwan4','luci-i18n-mwan4-zh-cn'} if a.variant=='mwan4' else {'pbr','luci-app-pbr','luci-i18n-pbr-zh-cn'}
 forbidden={'mwan3','luci-app-mwan3','vpn-policy-routing'}|({'pbr','luci-app-pbr'} if a.variant=='mwan4' else {'mwan4','luci-app-mwan4'})
 assert wanted<=selected and not forbidden&selected,(wanted-selected,forbidden&selected)
 if (P/'package-inputs.json').exists():
  for rel,h in json.loads((P/'package-inputs.json').read_text())[a.variant].items():assert sha(S/rel)==h,'Package input drift: '+rel
 assert 'LINUX_VERSION-6.18 = .60' in (S/'target/linux/generic/kernel-6.18').read_text()
 dts=(S/'target/linux/airoha/dts/an7581.dtsi').read_text();hz=[int(x) for x in re.findall(r'opp-hz\s*=\s*/bits/\s*64\s*<\s*(\d+)',dts)]
 assert hz and max(hz)==1200000000,hz
 assert not list((S/'target/linux/airoha/patches-6.18').glob('*overclock*'))
 for f in (S/'files').rglob('*'):
  assert not (f.is_file() and any(x in f.name for x in ['cn-split','cn_split','fakeip','mwan4-rule-guard','mwan4-preset'])),f
 print('PASS exact 6.18.60, full package closure, native CPU, exclusive '+a.variant+' and no baked personal routing')
