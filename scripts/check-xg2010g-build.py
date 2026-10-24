#!/usr/bin/env python3
"""Reject firmware missing the requested Airoha snapshot or four-core view."""
import argparse
import hashlib
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
root = args.source
meta = json.loads((root / 'files/etc/airoha-build-source.json').read_text())
expected = {
    'naoki': ('gbosek/luci-app-airoha', 'f8c1bc6872b36bc5445fd0946103d65b1f736d7b', r'^2\.0\.0-(?:r)?907$'),
    'luanmuc': ('luanmuc/luci-app-airoha-npu', '5c6e9e079ad9ecb1446c674e964f797842675856', r'^1\.2\.1-(?:r)?102$'),
}
variant = meta['variant']
upstream, commit, version_pattern = expected[variant]
assert meta['upstream'] == upstream and meta['commit'] == commit, 'NPU provider SHA mismatch'
backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
assert "popen('/usr/libexec/xg2010g-cpuusage')" in backend.read_text(), 'Native CPU helper RPC absent'
assert 'cpuSampleDisplay(cpuusage)' in page.read_text(), 'Native CPU overview absent'
manifest_dir = root / 'bin/targets/airoha/an7581'
manifests=list(manifest_dir.glob('*.manifest'))
assert manifests, 'No firmware manifest'
for manifest in manifests:
    pkgs = dict(re.findall(r'^(\S+) - (.+)$', manifest.read_text(), re.M))
    assert re.match(r'^6\.18\.55(?:[.~+-]|$)',pkgs.get('kernel','')), 'Expected exactly Linux 6.18.55'
    assert 'ttyd' in pkgs and 'luci-app-ttyd' in pkgs, 'Requested web terminal missing'
    assert re.match(r'^3\.16\.0-(?:r)?1$', pkgs.get('rtp2httpd','')), 'Retained RTP backend version missing'
    assert 'luci-app-rtp2httpd' in pkgs, 'Retained RTP UI missing'
    assert not any(n.startswith(('wpad','hostapd','wpa-supplicant')) or n in
        ('coremark','luci-app-coremark','iw','iwinfo','wifi-scripts','wireless-regdb','kmod-mac80211','kmod-cfg80211') for n in pkgs), 'Unused wireless packages remain'

    for name in ('mwan4', 'luci-app-mwan4', 'luci-i18n-mwan4-zh-cn',
                 'luci-app-airoha-npu', 'luci-i18n-airoha-npu-zh-cn', 'xg2010g-rps', 'luci-app-pon-status',
                 'luci-app-wol', 'luci-i18n-wol-zh-cn', 'etherwake', 'flock',
                 'luci-theme-argon', 'luci-app-argon-config', 'luci-i18n-argon-config-zh-cn'):
        assert name in pkgs, f'{manifest.name}: missing {name}'
    assert pkgs['xg2010g-rps'].startswith('20261013'), 'Old RPS package'
    assert re.match(r'^20261013-(?:r)?3$', pkgs['xg2010g-rps']), 'RPS read/singleton fix missing'
    assert re.match(r'^0\.1\.1-(?:r)?9$', pkgs['mwan4']), 'MWAN4 routing fixes missing'
    assert re.match(r'^1\.0\.0-(?:r)?12$', pkgs['luci-app-mwan4']), 'MWAN4 stopped-state editing fix missing'
    assert re.search(r'-(?:r)?9$', pkgs['luci-app-pon-status']), 'PON fullwidth-v3 package release missing'
    assert not any(n in pkgs for n in ('mwan3', 'mwan3-nft', 'luci-app-mwan3')), 'Mixed MWAN stacks'
    assert re.match(version_pattern, pkgs['luci-app-airoha-npu']), 'Wrong NPU package/local adapter revision'
    assert not any(n in pkgs for n in ('luci-app-nlbwmon','luci-app-statistics')), 'Removed monitor/statistics plugin present'
    for name in ('cpufreq','luci-app-cpufreq','luci-i18n-cpufreq-zh-cn'):
        assert name in pkgs, f'Missing CPU policy package: {name}'
# Validate installed files before releasing any sysupgrade image.
roots = list((root / 'build_dir').glob('target-*/root-airoha'))
assert len(roots) == 1, f'Expected one staged rootfs, got {len(roots)}'
installed = roots[0]
assert json.loads((installed / 'etc/airoha-build-source.json').read_text()) == meta
assert b"popen('/usr/libexec/xg2010g-cpuusage')" in (installed / 'usr/share/rpcd/ucode/luci').read_bytes()
assert 'cpuSampleDisplay(cpuusage)' in (installed / 'www/luci-static/resources/view/status/include/10_system.js').read_text()
cpu_page = (installed / 'www/luci-static/resources/view/status/include/10_system.js').read_text()
assert 'cpu-sample-values' in cpu_page and 'SYS 含 system / IRQ / softirq' not in cpu_page, 'Verbose CPU display remains in image'
expected_cpu = Path(__file__).resolve().parents[1] / 'files/sbin/cpuusage'
cpu = installed / 'sbin/cpuusage'
assert cpu.is_file() and cpu.stat().st_mode & 0o111, 'Missing executable native CPU usage helper'
assert cpu.read_bytes() == expected_cpu.read_bytes(), 'CPU usage helper differs from repository source'
assert not (installed / 'files/sbin/cpuusage').exists(), 'Nested CPU usage overlay found'
assert '/usr/libexec/xg2010g-cpuusage' in cpu.read_text(), 'Compatibility CPU wrapper missing'
expected_temp = Path(__file__).resolve().parents[1] / 'files/sbin/tempinfo'
temp = installed / 'sbin/tempinfo'
assert temp.is_file() and temp.stat().st_mode & 0o111, 'Missing executable /sbin/tempinfo in rootfs'
assert temp.read_bytes() == expected_temp.read_bytes(), 'Temperature script differs from the requested overlay'
for label in ('CPU:', 'PON:', 'LAN1:', 'LAN2:'):
    assert label in temp.read_text(), f'Missing temperature sensor: {label}'
assert "popen('/sbin/tempinfo')" in (installed / 'usr/share/rpcd/ucode/luci').read_text(), 'RPC temperature path differs'
assert not (installed / 'files/sbin/tempinfo').exists(), 'Nested /files overlay found in rootfs'
if variant == 'naoki':
    path = installed / 'etc/init.d/airoha-npu'
    assert path.is_file() and path.stat().st_mode & 0o111, 'Manual CPU alias missing'
    assert not re.search(r'^START=', path.read_text(), re.M), 'Duplicate CPU boot owner'
repo = Path(__file__).resolve().parents[1]
stable = json.loads((installed / 'etc/kernel-stable-backport.json').read_text())
assert stable['kernel'] == '6.18.55' and stable['project'] == 'pon', 'Installed stable-kernel provenance mismatch'
assert stable['tarball_sha256'] == 'f410638061a165c12f42ab871d2f3fcd525515359b5faeee80969cff84524df9'
assert stable['patch_sha256'] == hashlib.sha256((repo / 'source-patches/pon-6.18.54-to-6.18.55.patch').read_bytes()).hexdigest()
driver_meta = json.loads((repo / 'AN7581-DRIVER-FIXES-SOURCE.json').read_text())
driver_meta.update(project='pon', selected_baseline=driver_meta['baselines']['pon'])
assert json.loads((installed / 'etc/an7581-driver-fixes.json').read_text()) == driver_meta, 'Installed upstream driver-fix provenance mismatch'
assert json.loads((installed / 'etc/phy-rtl826x-source.json').read_text()) == json.loads((repo / 'PHY-RTL826X-SOURCE.json').read_text()), 'Installed PHY provenance mismatch'
for rel in ('usr/bin/rps-guard.sh','usr/bin/rps-watch.sh','etc/init.d/xg2010g-rps',
            'etc/hotplug.d/iface/99-rps-guard','etc/init.d/npu-jitter','usr/libexec/npu-jitter-daemon',
            'etc/uci-defaults/96-wifi-5g-cn'):
    assert not (installed / rel).exists(), 'Removed periodic/wireless task remains: '+rel
for src in (repo/'Runtime/root').rglob('*'):
    if not src.is_file(): continue
    rel=src.relative_to(repo/'Runtime/root'); dest=installed/rel
    assert dest.is_file() and dest.read_bytes()==src.read_bytes(), 'Runtime migration/sample differs: '+str(rel)
    if src.suffix != '.awk': assert dest.stat().st_mode & 0o111, 'Nonexecutable runtime: '+str(rel)
assert "[ _('卸载') ]" in (repo/'UI/15_pon.js').read_text()
assert 'HW_OFFLOAD 标记连接' not in (repo/'UI/15_pon.js').read_text()
assert 'packet_steering' in (installed/'etc/init.d/packet_steering').read_text()
ppe_rpc=(installed/'usr/libexec/rpcd/luci.airoha_npu').read_text()
assert 'getPpeExport' in ppe_rpc and '/usr/libexec/airoha-ppe-snapshot.sh' in ppe_rpc
ppe_js=(installed/'www/luci-static/resources/view/airoha_npu/status.js').read_text()
assert '完整导出 JSON' in ppe_js and '后端已截断' in ppe_js and 'captured_at' in ppe_js
for rel, filename in [('usr/libexec/airoha-ppe.awk','airoha-ppe.awk'),
                      ('usr/libexec/airoha-ppe-snapshot.sh','airoha-ppe-snapshot.sh'),
                      ('usr/libexec/airoha-deadline.sh','airoha-deadline.sh')]:
    assert (installed/rel).read_bytes()==(repo/'Runtime'/filename).read_bytes(), 'PPE runtime differs: '+rel
sampler=(installed/'usr/libexec/xg2010g-cpuusage').read_text()
assert 'last_success_at' in sampler and 'proc_stat_unreadable' in sampler
assert all(token in cpu_page for token in ('sample.stale', 'sample.error',
    'sample.last_success_at', 'cpu-sample-warning', '（旧数据）')), 'CPU stale-sample warning missing'
assert '最后有效样本' not in cpu_page, 'Hidden CPU sampling details remain in image'
mwan_init=(installed/'etc/init.d/mwan4').read_text()
assert 'mwan4-rule-guard.sh --cleanup' in mwan_init and 'mwan4-rule-guard.sh --routes-only' in mwan_init
pon_include = installed / 'www/luci-static/resources/view/status/include/15_xg2010g_pon.js'
assert pon_include.read_bytes() == (repo / 'UI/15_pon.js').read_bytes(), 'Dedicated full-width PON view missing'
assert not (pon_include.parent / '15_pon.js').exists(), 'Legacy PON module would create a duplicate/cached card'
layout = json.loads((installed / 'etc/pon-status-layout.json').read_text())
assert layout['layout'] == 'fullwidth-v3' and layout['module'] == 'view.status.include.15_xg2010g_pon'
assert layout['sha256'] == hashlib.sha256(pon_include.read_bytes()).hexdigest(), 'PON layout provenance mismatch'
overview = (installed / 'www/luci-static/resources/view/mwan4/network/overview.js').read_text()
assert 'Service stopped' in overview and 'Service did not reach the requested state.' in overview, 'MWAN4 stop confirmation missing'
assert '192.168.10.1' in (installed / 'bin/config_generate').read_text(), 'Default LAN IP missing'
assert 'create_iface_rules(iface, l3_device)' in (installed / 'lib/mwan4/mwan4.uc').read_text(), 'Native MWAN4 init rules missing'
assert not (installed / 'etc/uci-defaults/98-xg2010g-mwan4-defaults').exists(), 'Preset must wait for explicit start'
for relative in ('etc/uci-defaults/99-xg2010g-mwan4-default-off', 'usr/libexec/xg2010g-mwan4-preset'):
    path = installed / relative
    assert path.stat().st_mode & 0o111 and path.read_bytes() == (repo / 'files' / relative).read_bytes(), relative
assert 'enabled || return 0' in mwan_init and 'service_running || return 0' in mwan_init
assert 'procd_running mwan4' in mwan_init, 'Status directory must not be treated as a running service'
assert '/usr/libexec/xg2010g-mwan4-preset || return 1' in mwan_init
assert 'wasRunning' in overview and 'Service remains stopped.' in overview
assert 'withButtonBusy(eventButton(ev), refreshRuntime)' in overview
assert "action == 'stop' ? 'disable' : 'enable'" in (installed / 'usr/share/rpcd/ucode/mwan4').read_text()
assert 'm.init();' not in (installed / 'usr/share/rpcd/ucode/mwan4').read_text()
assert json.loads((installed / 'etc/xg2010g-mwan4-source.json').read_text()) == json.loads((repo / 'MWAN4-SOURCE.json').read_text())
assert (installed / 'etc/upstream-059895-source.json').read_bytes() == (repo / 'UPSTREAM-059895-SOURCE.json').read_bytes()
assert (installed / 'www/luci-static/resources/view/wol.js').is_file(), 'WOL page missing'
assert (installed / 'usr/bin/etherwake').stat().st_mode & 0o111, 'WOL packet sender missing'
assert (installed / 'www/luci-static/resources/view/status/index.js').read_bytes() == (repo / 'UI/status-index.js').read_bytes(), 'Independent overview card loading missing'
assert (installed / 'www/luci-static/resources/view/argon-config.js').is_file(), 'Argon wallpaper configuration missing'
assert "option online_wallpaper 'bing'" in (installed / 'etc/config/argon').read_text(), 'Bing wallpaper default missing'
wallpaper = installed / 'usr/libexec/rpcd/luci.argon_wallpaper'
assert wallpaper.is_file() and wallpaper.stat().st_mode & 0o111, 'Argon wallpaper provider missing'
print(variant + ': Latest Airoha snapshot, MWAN4, Chinese UI, four CPU cores, RPS boot/event policy and CPU/PON/LAN1/LAN2 temperature script verified in staged rootfs')
print('Verified MWAN4 stop/native-init fixes, RPS boot/event policy, full-width PON, WOL and default LAN 192.168.10.1')
print('Verified independent overview rendering and Argon Chinese wallpaper configuration with Bing default')
print('Verified PON fullwidth-v3, compact transparent rate rows, package r9 and layout provenance')
assert (installed/'etc/config/fstab').is_file(), 'Default fstab missing from delivered rootfs'
boot = json.loads((installed/'etc/xg2010g-boot-fixes.json').read_text())
assert boot['phy_patch_sha256'] == hashlib.sha256((repo/'kernel-patches/airoha'/boot['phy_patch']).read_bytes()).hexdigest()
busybox_configs = list((root/'build_dir').glob('target-*/busybox-default/busybox-*/.config'))
assert busybox_configs, 'Compiled BusyBox configuration missing'
for busybox_config in busybox_configs:
    assert 'CONFIG_FEATURE_SYSLOG_INFO=y' in busybox_config.read_text().splitlines(), 'BusyBox still maps INFO to ERR'
print('Verified ROM fstab, boot fix provenance and compiled BusyBox INFO logging')

# Verify the changes in the delivered rootfs, not just the repository overlay.
led = json.loads((installed/'etc/xg2010g-led-fixes.json').read_text())
assert led['patch_sha256'] == hashlib.sha256((repo/'Boot/xg2010g-lan34-leds.patch').read_bytes()).hexdigest()
rel = 'etc/uci-defaults/99-xg2010g-lan34-led-mode'
assert (installed/rel).stat().st_mode & 0o111 and (installed/rel).read_bytes() == (repo/'Boot/root'/rel).read_bytes()
library = (installed/'lib/mwan4/mwan4.uc').read_text()
assert 'mwan4.mmx_default, mwan4.mmx_mask, mwan4.mmx_blackhole, mwan4.mmx_mask, mwan4.mmx_unreachable' in library, 'Reserved marks must not enter sticky cache'
rtmon = (installed/'lib/mwan4/mwan4rtmon.uc').read_text().split('function add_all_routes() {',1)[1].split('function handle_route(',1)[0]
assert 'route add table' not in rtmon and rtmon.count('route replace table') == 2, 'Route snapshots are not idempotent'
assert not (installed/'etc/uci-defaults/98-xg2010g-mwan4-defaults').exists()
for rel in ('etc/uci-defaults/99-xg2010g-mwan4-default-off', 'usr/libexec/xg2010g-mwan4-preset'):
    assert (installed/rel).stat().st_mode & 0o111 and (installed/rel).read_bytes() == (repo/'files'/rel).read_bytes(), rel
assert (installed/'usr/share/xg2010g/mwan4-stock.config').is_file()
assert json.loads((installed/'etc/xg2010g-mwan4-source.json').read_text()) == json.loads((repo/'MWAN4-SOURCE.json').read_text())
print('Verified LAN3/LAN4 migration, provider-DNS routing, reserved sticky marks, repeatable route snapshots and explicit-start defaults')
compat = json.loads((installed/'etc/firmware-package-compat.json').read_text())
assert compat == json.loads((repo/'BASELINE-PACKAGE-COMPAT.json').read_text()), 'Package compatibility provenance differs'
binary = (installed/'usr/bin/rtp2httpd').read_bytes()
assert binary[:4] == b'\x7fELF' and binary[18:20] == b'\xb7\0', 'RTP backend missing or not AArch64'
for name, path in [('files/rtp2httpd.config', 'etc/config/rtp2httpd'), ('files/rtp2httpd.init', 'etc/init.d/rtp2httpd')]:
    assert hashlib.sha256((installed/path).read_bytes()).hexdigest() == compat['files_sha256'][name], path
print('Verified existing rtp2httpd backend and unchanged disabled default in actual staged rootfs')
