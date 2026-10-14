#!/usr/bin/env python3
"""Select the pinned naoki ONU stack for the naoki NPU variant, retaining the requested overview card."""
import argparse,json,re,subprocess
from pathlib import Path

SHA='35e2d676c31f2ff510960fb03a403599d292a535'
URL='https://github.com/naoki66/OpenWrt_ONU_CONFIG.git'
OLD=['luci-app-pon','luci-i18n-pon-zh-cn','luci-app-iptv','luci-i18n-iptv-zh-cn']
NEW=['airoha-pond','airoha-ponctl','airoha-pon-debug','luci-app-onu','luci-i18n-onu-zh-cn','luci-app-pon-status']

def select_feed(root,repo):
 conf=root/'feeds.conf.default';s=conf.read_text()
 pattern=r'^src-[\w-]+\s+pon_userspace\s+\S+.*$'
 matches=re.findall(pattern,s,re.M);assert len(matches)==1,'Expected one existing PON userspace feed'
 line='src-git pon_userspace '+URL+'^'+SHA
 conf.write_text(re.sub(pattern,line,s,flags=re.M))
 (root/'files/etc').mkdir(parents=True,exist_ok=True)
 (root/'files/etc/pon-build-source.json').write_bytes((repo/'PON-SOURCE.json').read_bytes())

def configure(root):
 cfg=root/'.config';s=cfg.read_text()
 for name in OLD+NEW:
  key='CONFIG_PACKAGE_'+name
  s=re.sub(r'^(?:'+re.escape(key)+r'=.*|# '+re.escape(key)+r' is not set)\n?','',s,flags=re.M)
 s+='\n'+''.join('CONFIG_PACKAGE_'+p+'=n\n' for p in OLD)+''.join('CONFIG_PACKAGE_'+p+'=y\n' for p in NEW)+'CONFIG_FEED_pon_userspace=y\n'
 cfg.write_text(s)

def verify(root):
 feed=root/'feeds/pon_userspace'
 head=subprocess.check_output(['git','-C',str(feed),'rev-parse','HEAD'],text=True).strip();assert head==SHA,'PON feed commit mismatch'
 for path in ['airoha-pon-daemons','airoha-ponctl','airoha-pon-debug','luci-app-onu']:
  assert (feed/path/'Makefile').is_file(),path
 menu=json.loads((feed/'luci-app-onu/root/usr/share/luci/menu.d/luci-app-onu.json').read_text())
 assert 'admin/onu' in menu and 'admin/onu/internet' in menu and 'admin/onu/iptv' in menu
 assert (feed/'luci-app-onu/po/zh_Hans/onu.po').is_file()
 status=(feed/'airoha-ponctl/src/src/status.rs').read_text();assert 'temperature_celsius' in status and 'voltage_volts' in status
 for p in (feed/'luci-app-onu/root/usr/libexec').iterdir():assert p.stat().st_mode&0o111,'ONU helper not executable: '+p.name

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--variant',choices=['naoki','luanmuc'],required=True);p.add_argument('--phase',choices=['feed','config','verify'],required=True);a=p.parse_args()
 if a.variant=='naoki':
  root=a.source.resolve();repo=Path(__file__).resolve().parents[1]
  if a.phase=='feed':select_feed(root,repo)
  elif a.phase=='config':configure(root)
  else:verify(root)
  print('naoki ONU '+a.phase+' selection verified at '+SHA)
