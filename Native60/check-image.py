#!/usr/bin/env python3
from pathlib import Path
import argparse,json,os,re,hashlib
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--root',type=Path,required=True);a=p.parse_args();S=a.source;root=a.root;P=Path(__file__).resolve().parent;R=P.parent;v=os.environ['ROUTING_VARIANT']
pkgs={}
for block in (root/'lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(l.split(':',1) for l in block.splitlines() if l.startswith(('P:','V:')))
 if 'P' in f:pkgs[f['P']]=f['V']
baseline={l.split(' - ',1)[0] for l in ((R/'StableRefresh/baseline.manifest').read_text()+(R/'StableRefresh/current-installed.manifest').read_text()).splitlines() if ' - ' in l}
omit={'kernel','luci-app-argon-config'}
if v=='pbr':omit|={'mwan4','luci-app-mwan4','luci-i18n-mwan4-zh-cn'}
assert not baseline-omit-pkgs.keys(),sorted(baseline-omit-pkgs.keys())
expected={'mwan4':'0.1.1-r30','luci-app-mwan4':'1.0.0-r19','luci-i18n-mwan4-zh-cn':'1.0.0-r19'} if v=='mwan4' else {'pbr':'1.2.4-r2','luci-app-pbr':'1.2.4-r2'}
expected|={'luci-app-airoha-npu':'2.0.0-r901','luci-app-pon-status':'0.1.0-r13','luci-theme-argon':'3.1.3-r20261106'}
for n,ver in expected.items():assert pkgs.get(n)==ver,(n,pkgs.get(n),ver)
for n in (['pbr','luci-app-pbr'] if v=='mwan4' else ['mwan4','luci-app-mwan4']):assert n not in pkgs,n
assert re.match(r'^6\.18\.60(?:[.~+-]|$)',pkgs.get('kernel',''))
assert not (root/'usr/libexec/xg2010g-cpu-policy').exists()
assert not (root/'usr/sbin/xg-cn-split-setup').exists()
for rel in ['usr/libexec/airoha-npu-memory','usr/libexec/rpcd/luci.airoha_npu']:
 assert (root/rel).read_bytes()==(S/'package/custom/luci-app-airoha-npu/root'/rel).read_bytes(),rel
# LuCI minifies JS at packaging time. Compare the image with that build's
# actual installed output, while the package input pin is checked separately.
rel='www/luci-static/resources/view/airoha_npu/status.js'
staged=list((S/'build_dir').glob('target-*/root-airoha/'+rel))
assert len(staged)==1 and staged[0].read_bytes()==(root/rel).read_bytes(),rel
assert (root/'usr/libexec/airoha-npu-memory').stat().st_mode&0o111
assert json.loads((root/'etc/native60-source.json').read_text())==json.loads((P/'source.json').read_text())|{'variant':v}
assert '2026.11.14-native60-'+v in (root/'etc/openwrt_release').read_text()
for name in ['npu-jitter','airoha-npu']:assert (root/'etc/init.d'/name).stat().st_mode&0o111
if v=='pbr':assert (root/'usr/lib/lua/luci/i18n/pbr.zh-cn.lmo').is_file()
print('PASS actual FIT rootfs: full baseline, exclusive '+v+', correct versions, latest Airoha plus DT memory fix, no overclock or personal routing presets')
