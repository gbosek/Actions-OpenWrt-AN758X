#!/usr/bin/env python3
"""Reject an XG2010G build with stale kernel, periodic helpers or wireless defaults."""
from pathlib import Path
import argparse, json, re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
root=p.parse_args().source.resolve()
repo=Path(__file__).resolve().parents[1]
version=(root/'target/linux/generic/kernel-6.18').read_text()
assert re.search(r'^LINUX_VERSION-6\.18 = \.54$',version,re.M),'Expected Linux 6.18.54'
assert 'LINUX_KERNEL_HASH-6.18.54 = 9df30b02dd8102bbd0be52556288ef6889ddbe7f1ddb96fbf847d0becf3eacac' in version
config=(root/'.config').read_text()
selected=set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=[ym]$',config,re.M))
assert {'ttyd','luci-app-ttyd','cpufreq','xg2010g-rps'}<=selected,'Required runtime packages missing'
assert not any(x.startswith(('wpad','hostapd','wpa-supplicant')) or x in
 ('coremark','luci-app-coremark','iw','iwinfo','wireless-regdb','wifi-scripts','kmod-mac80211','kmod-cfg80211') for x in selected),'Unused WiFi stack selected'
app=root/'package/custom/luci-app-airoha-npu'
assert not (app/'root/etc/init.d/npu-jitter').exists()
assert not (app/'root/usr/libexec/npu-jitter-daemon').exists()
assert not (root/'files/etc/uci-defaults/96-wifi-5g-cn').exists()
init=(root/'package/emortal/cpufreq/files/cpufreq.init').read_text()
assert 'START=89' in init and 'xg2010g-cpu-policy apply' in init
assert 'xg2010g-cpu-policy watch' not in init and 'procd_set_param respawn' not in init
assert 'watch)' not in (root/'package/emortal/cpufreq/files/xg2010g-cpu-policy').read_text()
rps=(root/'package/custom/xg2010g-rps/Makefile').read_text()
assert 'rps-watch' not in rps and 'rps-guard' not in rps and 'xg2010g-rps.init' not in rps
for source in (repo/'Runtime/root').rglob('*'):
 if source.is_file():assert (root/'files'/source.relative_to(repo/'Runtime/root')).read_bytes()==source.read_bytes()
rpc=(root/'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci').read_text()
assert "popen('/usr/libexec/xg2010g-cpuusage')" in rpc and 'cpu_sampler_invalid_json' in rpc
page=(root/'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js').read_text()
assert 'cpuSampleDisplay(cpuusage)' in page and "'cpu-sample-values'" in page
assert 'SYS 含 system / IRQ / softirq' not in page, 'Verbose CPU diagnostics still shown'
queue=root/'target/linux/airoha/patches-6.18'
for number in (931,932,933,934,935,937,999):assert len(list(queue.glob(str(number)+'-*.patch')))==1,number
assert not list(queue.glob('936-*rx*patch')),'RX31 is native in 6.18.54'
print('PASS: Linux 6.18.54, boot/event policy, ttyd, no WiFi/jitter, structured CPU/PPE observability and expected driver patch queue')
