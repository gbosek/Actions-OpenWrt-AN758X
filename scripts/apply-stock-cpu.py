#!/usr/bin/env python3
"""Keep upstream BL31/DTS unchanged and install a 500–1200MHz dynamic policy."""
from pathlib import Path
import argparse,json,re,shutil
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args()
root=a.source.resolve();repo=Path(__file__).resolve().parents[1]
assert (root/'target/linux/airoha/an7581/config-6.18').is_file()
queue=root/'target/linux/airoha/patches-6.18'
for pattern in ['999*overclock*','936*pll*','937*pll*','0401*pll*','0402*pll*']:
 assert not list(queue.glob(pattern)), 'Unexpected overclock patch in stock build'
board=(root/'target/linux/airoha/dts/an7581-gemtek-xg2010g.dts').read_text()
for forbidden in ['gemtek,1400mhz-boost','airoha,force-direct-pll','opp-1400000000','cpufreq.default_governor=powersave']:
 assert forbidden not in board, 'Unexpected boost change in stock DTS: '+forbidden
pkg=root/'package/emortal/cpufreq'
for name in ['cpufreq.init','cpufreq.uci','xg2010g-cpu-policy']:
 shutil.copyfile(repo/'CPU/runtime'/name,pkg/'files'/name);(pkg/'files'/name).chmod(0o755)
make=pkg/'Makefile';s=re.sub(r'^PKG_RELEASE:=.*$','PKG_RELEASE:=4',make.read_text(),flags=re.M)
if '$(1)/usr/libexec/xg2010g-cpu-policy' not in s:
 marker='	$(INSTALL_BIN) $(CURDIR)/files/cpufreq.init $(1)/etc/init.d/'
 assert marker in s
 s=s.replace(marker,marker+'\n\t$(INSTALL_DIR) $(1)/usr/libexec\n\t$(INSTALL_BIN) $(CURDIR)/files/xg2010g-cpu-policy $(1)/usr/libexec/xg2010g-cpu-policy')
make.write_text(s)
(root/'files/etc').mkdir(parents=True,exist_ok=True)
shutil.copyfile(repo/'CPU-BOOST-SOURCE.json',root/'files/etc/xg2010g-cpu-boost-source.json')
print('Installed stock BL31 dynamic 500–1200MHz policy; kernel and board DTS unchanged')
