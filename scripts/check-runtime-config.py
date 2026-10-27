#!/usr/bin/env python3
"""Reject an XG2010G build with stale kernel, periodic helpers or wireless defaults."""
from pathlib import Path
import argparse, json, re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
root=p.parse_args().source.resolve()
repo=Path(__file__).resolve().parents[1]
version=(root/'target/linux/generic/kernel-6.18').read_text()
assert re.search(r'^LINUX_VERSION-6\.18 = \.55$',version,re.M),'Expected Linux 6.18.55'
assert 'LINUX_KERNEL_HASH-6.18.55 = f410638061a165c12f42ab871d2f3fcd525515359b5faeee80969cff84524df9' in version
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
for number in (931,932,933,934,937,938,999):assert len(list(queue.glob(str(number)+'-*.patch')))==1,number
assert 'CONFIG_BUSYBOX_CONFIG_FEATURE_SYSLOG_INFO=y' in config, 'BusyBox INFO logging missing'
assert (root/'files/etc/config/fstab').is_file(), 'ROM fstab missing'
assert not list(queue.glob('935-*patch')),'NPU watchdog fix is native in 6.18.55'
assert not list(queue.glob('936-*rx*patch')),'RX31 is native in 6.18.55'
init=(root/'package/custom/mwan4/files/etc/init.d/mwan4').read_text()
assert 'enabled || return 0' in init and 'service_running || return 0' in init
assert '/usr/libexec/xg2010g-mwan4-preset || return 1' in init
assert (root/'files/etc/config/mwan4').read_bytes() == (repo/'files/etc/config/mwan4').read_bytes()
assert (root/'package/custom/mwan4/files/etc/config/mwan4').read_bytes() == (repo/'files/etc/config/mwan4').read_bytes()
metadata=json.loads((repo/'MWAN4-SOURCE.json').read_text())
for kind,name in [('backend','mwan4'),('frontend','luci-app-mwan4')]:
 expected=metadata[kind]['version'].rsplit('-r',1)[1]
 make=(root/'package/custom'/name/'Makefile').read_text()
 assert re.search(r'^PKG_RELEASE:='+re.escape(expected)+r'$',make,re.M), 'MWAN4 package release differs from source metadata: '+name
assert not (root/'files/etc/uci-defaults/98-xg2010g-mwan4-defaults').exists()
assert (root/'files/etc/uci-defaults/99-xg2010g-mwan4-default-off').stat().st_mode & 0o111
print('PASS: Linux 6.18.55, boot/event policy, ttyd, no WiFi/jitter, structured CPU/PPE observability and expected driver patch queue')
