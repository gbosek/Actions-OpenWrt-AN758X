#!/usr/bin/env python3
"""Check selected ONU source, configuration and installed files before release."""
import argparse,importlib.util,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--variant',required=True,choices=['naoki','luanmuc']);p.add_argument('--config-only',action='store_true');a=p.parse_args();root=a.source.resolve()
if a.variant=='naoki':
 spec=importlib.util.spec_from_file_location('pon',Path(__file__).with_name('select-pon.py'));pon=importlib.util.module_from_spec(spec);spec.loader.exec_module(pon)
 pon.verify(root)
 cfg=(root/'.config').read_text()
 for name in pon.NEW:assert re.search(r'^CONFIG_PACKAGE_'+re.escape(name)+r'=y$',cfg,re.M),'Missing ONU package '+name
 for name in pon.OLD:assert not re.search(r'^CONFIG_PACKAGE_'+re.escape(name)+r'=y$',cfg,re.M),'Old PON/IPTV package still selected: '+name
 if not a.config_only:
  manifests=list((root/'bin/targets/airoha/an7581').glob('*.manifest'));assert manifests,'Firmware manifest absent'
  for f in manifests:
   packages=dict(re.findall(r'^(\S+) - (.+)$',f.read_text(),re.M))
   for name in pon.NEW:assert name in packages,'Missing installed ONU package '+name
   for name in pon.OLD:assert name not in packages,'Old PON package in image: '+name
   assert packages['luci-app-onu'] in ['0.1.0-r25','0.1.0-25'],'Wrong ONU UI release'
  roots=list((root/'build_dir').glob('target-*/root-airoha'));assert len(roots)==1;installed=roots[0]
  assert json.loads((installed/'etc/pon-build-source.json').read_text())['commit']==pon.SHA
  feed=root/'feeds/pon_userspace/luci-app-onu/root'
  for rel in ['usr/share/luci/menu.d/luci-app-onu.json','usr/share/rpcd/acl.d/luci-app-onu.json']:
   assert (installed/rel).read_bytes()==(feed/rel).read_bytes(),rel
  for name in ['internet-apply','iptv-apply','voice-apply','pon-board-identity','airoha-pon-data']:
   path=installed/'usr/libexec'/name;assert path.stat().st_mode&0o111 and path.read_bytes()==(feed/'usr/libexec'/name).read_bytes(),name
  for name in ['ponctl','airoha-pond','pon-debug']:assert (installed/'usr/sbin'/name).stat().st_mode&0o111,name
  for name in ['onu-internet','onu-iptv','onu-voice','pon']:assert (installed/'etc/config'/name).is_file(),name
 print('naoki ONU source/configuration'+(' and actual rootfs/manifest' if not a.config_only else '')+' verified')
else:print('luanmuc keeps its repository-default PON selection')
