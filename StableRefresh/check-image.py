#!/usr/bin/env python3
from pathlib import Path
import argparse,re,json
parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('--root',type=Path,help='Extracted rootfs from the final FIT image')
args=parser.parse_args();S=args.source;P=Path(__file__).resolve().parent
manifests=(P/'baseline.manifest').read_text()+(P/'current-installed.manifest').read_text()
baseline={line.split(' - ',1)[0] for line in manifests.splitlines() if ' - ' in line}-{'kernel','luci-app-argon-config'}
manifests=list((S/'bin/targets/airoha/an7581').glob('*gemtek_xg2010g.manifest'));assert len(manifests)==1
if args.root is not None:
 root=args.root
else:
 roots=list((S/'build_dir').glob('target-*/linux-airoha_an7581/target-dir-*'))
 assert len(roots)==1,'Pass --root for the final extracted image when a unique device rootfs is unavailable'
 root=roots[0]
# Per-device hidden packages may be omitted from the global build manifest.
packages={}
for block in (root/'lib/apk/db/installed').read_text().split('\n\n'):
 fields=dict(line.split(':',1) for line in block.splitlines() if line.startswith(('P:','V:')))
 if 'P' in fields and 'V' in fields:packages[fields['P']]=fields['V']
assert not baseline-packages.keys(),'Missing baseline functionality: '+str(sorted(baseline-packages.keys()))
for name,version in [('mwan4','0.1.1-r30'),('luci-app-mwan4','1.0.0-r19'),('luci-i18n-mwan4-zh-cn','1.0.0-r19'),('luci-app-pon-status','0.1.0-r13'),('luci-theme-argon','3.1.3-r20261106')]:
 assert packages.get(name)==version,(name,packages.get(name))
for rel in ['usr/bin/mwan4-rule-guard.sh','usr/libexec/xg2010g-mwan4-preset','usr/sbin/xg-cn-split-setup','etc/firewall.lan-fakeip.nft','etc/hotplug.d/iface/90-xg-cn-split','usr/share/nftables.d/ruleset-post/20-cn-split.nft']:
 assert (root/rel).read_bytes()==(P/'root'/rel).read_bytes(),rel
assert not (root/'usr/libexec/xg2010g-cpu-policy').exists()
assert not (root/'etc/uci-defaults/99-xg2010g-mwan4-default-off').exists()
for rel in ['etc/init.d/npu-jitter','usr/libexec/npu-jitter-daemon']:
 assert (root/rel).is_file() and (root/rel).stat().st_mode&0o111,rel
desc=(root/'etc/openwrt_release').read_text();assert '2026.11.09-refresh3' in desc and re.search(r'20\d\d-\d\d-\d\d \d\d:\d\d',desc),desc
assert json.loads((root/'etc/stable-refresh-source.json').read_text())==json.loads((P/'source.json').read_text())
print('PASS actual installed-package database, live safeguards, dated version and no custom overclock helper')
