#!/usr/bin/env python3
from pathlib import Path
import sys,re,json
S=Path(sys.argv[1]);P=Path(__file__).resolve().parent
baseline={l.split(' - ',1)[0] for l in (P/'baseline.manifest').read_text().splitlines() if ' - ' in l}-{'kernel','luci-app-argon-config'}
manifests=list((S/'bin/targets/airoha/an7581').glob('*gemtek_xg2010g.manifest'));assert len(manifests)==1
packages=dict(l.split(' - ',1) for l in manifests[0].read_text().splitlines() if ' - ' in l)
assert not baseline-packages.keys(),'Missing baseline functionality: '+str(sorted(baseline-packages.keys()))
for name,version in [('mwan4','0.1.1-r30'),('luci-app-mwan4','1.0.0-r19'),('luci-i18n-mwan4-zh-cn','1.0.0-r19'),('luci-app-pon-status','0.1.0-r13'),('luci-theme-argon','3.1.3-r20261106')]:
 assert packages.get(name)==version,(name,packages.get(name))
roots=list((S/'build_dir').glob('target-*/root-airoha'));assert len(roots)==1;root=roots[0]
for rel in ['usr/bin/mwan4-rule-guard.sh','usr/libexec/xg2010g-mwan4-preset','usr/sbin/xg-cn-split-setup','etc/firewall.lan-fakeip.nft','etc/hotplug.d/iface/90-xg-cn-split','usr/share/nftables.d/ruleset-post/20-cn-split.nft']:
 assert (root/rel).read_bytes()==(P/'root'/rel).read_bytes(),rel
assert not (root/'usr/libexec/xg2010g-cpu-policy').exists()
assert not (root/'etc/uci-defaults/99-xg2010g-mwan4-default-off').exists()
desc=(root/'etc/openwrt_release').read_text();assert '2026.11.09-refresh2' in desc and re.search(r'20\d\d-\d\d-\d\d \d\d:\d\d',desc),desc
assert json.loads((root/'etc/stable-refresh-source.json').read_text())==json.loads((P/'source.json').read_text())
print('PASS actual full package manifest, live safeguards, dated version and no custom overclock helper')
