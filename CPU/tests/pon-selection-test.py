#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess,json
repo=Path(__file__).resolve().parents[2];scripts=repo/('scripts' if (repo/'scripts/select-pon.py').exists() else 'Scripts')
with tempfile.TemporaryDirectory() as d:
 root=Path(d);conf=root/'feeds.conf.default';original='src-git packages https://github.com/immortalwrt/packages.git\nsrc-git pon_drivers https://github.com/pbs05/openwrt-pon-drivers.git\nsrc-git pon_userspace https://github.com/pbs05/openwrt-pon-userspace.git\n'
 conf.write_text(original);cfg=root/'.config';initial='CONFIG_PACKAGE_luci-app-pon=y\nCONFIG_PACKAGE_luci-app-iptv=y\nCONFIG_PACKAGE_luci-app-pon-status=y\nCONFIG_PACKAGE_mwan4=y\nCONFIG_PACKAGE_luci-app-airoha-npu=y\n';cfg.write_text(initial)
 def run(variant,phase):subprocess.run(['python3',str(scripts/'select-pon.py'),d,'--variant',variant,'--phase',phase],check=True)
 run('luanmuc','feed');run('luanmuc','config');assert conf.read_text()==original and cfg.read_text()==initial
 for _ in range(2):run('naoki','feed');run('naoki','config')
 assert conf.read_text().count('naoki66/OpenWrt_ONU_CONFIG.git^35e2d676c31f2ff510960fb03a403599d292a535')==1
 assert 'src-git pon_drivers https://github.com/pbs05/openwrt-pon-drivers.git' in conf.read_text()
 assert 'CONFIG_PACKAGE_mwan4=y' in cfg.read_text() and 'CONFIG_PACKAGE_luci-app-airoha-npu=y' in cfg.read_text()
 for name in ['luci-app-onu','luci-i18n-onu-zh-cn','airoha-pond','airoha-ponctl','airoha-pon-debug']:assert cfg.read_text().count('CONFIG_PACKAGE_'+name+'=y')==1
 for name in ['luci-app-pon','luci-app-iptv','luci-app-pon-status']:assert 'CONFIG_PACKAGE_'+name+'=y' not in cfg.read_text()
 assert json.loads((root/'files/etc/pon-build-source.json').read_text())['commit']=='35e2d676c31f2ff510960fb03a403599d292a535'
print('PASS: ONU feed pin/configuration replacement only for naoki, idempotent selection, original luanmuc feed and shared packages retained')
