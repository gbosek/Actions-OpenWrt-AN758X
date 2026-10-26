#!/usr/bin/env python3
"""Check exact requested features in staged firmware, not only config symbols."""
import json,re,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1];source=Path(sys.argv[1])
meta=json.loads((repo/'Packages/Extras/SOURCE.json').read_text())
for manifest in (source/'bin/targets/airoha/an7581').glob('*.manifest'):
    pkgs=dict(re.findall(r'^(\S+) - (.+)$',manifest.read_text(),re.M))
    for name in meta['requested_packages']:assert name in pkgs,'Missing requested plugin/backend '+name
installed,=list((source/'build_dir').glob('target-*/root-airoha'))
assert json.loads((installed/'etc/xg2010g-requested-plugins.json').read_text())==meta
assert json.loads((installed/'etc/xg2010g-upstream-source.json').read_text())==json.loads((repo/'Upstream/SOURCE.json').read_text())
assert not re.search(r'^\s*config\s+watchcat', (installed/'etc/config/watchcat').read_text(),re.M),'Watchcat must have no default reboot rules'
assert "DISTRIB_DESCRIPTION='XG2010G " in (installed/'etc/openwrt_release').read_text(),'Wrong firmware display brand'
assert 'XG2010G' in (installed/'etc/uci-defaults/98-xg2010g-display-name').read_text()
for name in ['xg2010g-dnsmasq-log-guard','rpcd/luci.airoha_npu','clients-probe','clients-dns']:
    path=installed/'usr/libexec'/name;assert path.is_file() and path.stat().st_mode&0o111,name
assert '/usr/libexec/xg2010g-dnsmasq-log-guard || return 1' in (installed/'etc/init.d/dnsmasq').read_text()
assert (installed/'usr/bin/pushbot/package_manager.sh').is_file(), 'Pushbot sourced package manager helper missing'
for name in ['timewol','watchcat','ddns','pbr','udpxy','msd_lite','upnp']:
    assert any(name in p.name for p in (installed/'usr/share/luci/menu.d').glob('*.json')) or (installed/'usr/lib/lua/luci/controller'/ (name+'.lua')).exists(),name
print('Verified requested plugin/backends, XG2010G brand, pre-start DHCP log guard and inactive Watchcat default')
