#!/usr/bin/env python3
"""XG2010G boot/event policy and board-specific package selection."""
import json, re, shutil, sys
from pathlib import Path
root = Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
repo = Path(__file__).resolve().parents[1]
assert (root / 'target/linux/airoha').is_dir()
for src in (repo / 'Runtime/root').rglob('*'):
    if not src.is_file(): continue
    dest = root / 'files' / src.relative_to(repo/'Runtime/root')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    if src.suffix != '.awk': dest.chmod(0o755)
for name in ('96-wifi-5g-cn',):
    (root/'files/etc/uci-defaults'/name).unlink(missing_ok=True)
config = root / '.config'
if config.exists():
    text = config.read_text()
    # The XG2010G has no radios; do not select wpad through DEFAULT_PACKAGES.
    banned = {'iw','iwinfo','wireless-regdb','wifi-scripts','luci-app-wireless',
              'kmod-cfg80211','kmod-mac80211','hostapd-common','coremark','luci-app-coremark'}
    for make in (root / 'package').rglob('Makefile'):
        if 'hostapd' in make.parts:
            banned.update(re.findall(r'^define Package/([\w.+-]+)\s*$', make.read_text(errors='replace'), re.M))
    banned.update({'wpad-basic','wpad-basic-mbedtls','wpad-basic-wolfssl','wpad-basic-openssl',
                  'wpad','wpad-mbedtls','wpad-wolfssl','wpad-openssl',
                  'wpad-mini','hostapd','hostapd-basic','hostapd-mini','wpa-supplicant',
                  'wpa-supplicant-basic','wpa-supplicant-mini'})
    lines = [line for line in text.splitlines() if not any(
        line.startswith('CONFIG_PACKAGE_'+name+'=') or line == '# CONFIG_PACKAGE_'+name+' is not set' for name in banned)]
    lines += ['# CONFIG_PACKAGE_'+name+' is not set' for name in sorted(banned)]
    # Explicit request: keep the LuCI web terminal installed and enabled.
    lines += ['CONFIG_PACKAGE_ttyd=y','CONFIG_PACKAGE_luci-app-ttyd=y','CONFIG_PACKAGE_luci-i18n-ttyd-zh-cn=y']
    config.write_text('\n'.join(lines)+'\n')
print('XG2010G: boot-once CPU, native event-driven steering, no radio daemons, ttyd enabled')

init = root / 'package/custom/mwan4/files/etc/init.d/mwan4'
if init.exists():
    text = init.read_text()
    if 'mwan4-rule-guard.sh --routes-only' not in text:
        marker = 'ucode -S -L /lib/mwan4 /lib/mwan4/init_setup.uc'
        assert text.count(marker)==1
        text = text.replace(marker, marker+'\n\t[ ! -x /usr/bin/mwan4-rule-guard.sh ] || /usr/bin/mwan4-rule-guard.sh --routes-only',1)
    if 'mwan4-rule-guard.sh --cleanup' not in text:
        text = text.replace('stop_service() {', 'stop_service() {\n\t[ ! -x /usr/bin/mwan4-rule-guard.sh ] || /usr/bin/mwan4-rule-guard.sh --cleanup',1)
    init.write_text(text)

patch='937-net-airoha-expose-flow-stats-capability.patch'
shutil.copyfile(repo/'kernel-patches/airoha'/patch, root/'target/linux/airoha/patches-6.18'/patch)

make=root/'package/custom/mwan4/Makefile'
if make.exists():
    text,n=re.subn(r'^PKG_RELEASE:=.*$', 'PKG_RELEASE:=7',make.read_text(),flags=re.M)
    assert n==1, 'MWAN4 package release definition changed'
    make.write_text(text)

if init.exists():
    text=init.read_text()
    if 'rm -f /var/run/mwan4-rule-guard.stopped' not in text:
        text=text.replace('start_service() {', 'start_service() {\n\trm -f /var/run/mwan4-rule-guard.stopped',1)
    if ': > /var/run/mwan4-rule-guard.stopped' not in text:
        text=text.replace('stop_service() {', 'stop_service() {\n\t: > /var/run/mwan4-rule-guard.stopped',1)
    init.write_text(text)

# Run after the runtime r7 adjustments on every invocation.
import importlib.util
spec = importlib.util.spec_from_file_location('mwan4_default_off', repo/'scripts/apply-mwan4-default-off.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.install(root)
shutil.copyfile(repo/'UPSTREAM-059895-SOURCE.json', root/'files/etc/upstream-059895-source.json')
