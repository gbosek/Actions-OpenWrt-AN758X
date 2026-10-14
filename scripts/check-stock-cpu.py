#!/usr/bin/env python3
"""Verify the actual stock CPU driver, FIT OPPs and installed policy."""
import argparse,importlib.util,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);root=p.parse_args().source.resolve()
spec=importlib.util.spec_from_file_location('fit',Path(__file__).with_name('check-compatible-boost.py'));fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
kernels=[p.parent for p in (root/'build_dir').glob('target-*/linux-*/linux-6.18.*/.config') if (p.parent/'drivers/pmdomain/mediatek/airoha-cpu-pmdomain.c').is_file()];assert len(kernels)==1
kernel=kernels[0];driver=kernel/'drivers/pmdomain/mediatek/airoha-cpu-pmdomain.c';body=driver.read_text()
assert 'xg2010g_boost' not in body and not (driver.parent/'xg2010g-cpu-boost.h').exists()
assert 'AIROHA_AVS_OP_FREQ_DYN_ADJ' in body and 'arm_smccc_1_1_invoke' in body
obj=driver.with_suffix('.o');assert obj.is_file() and b'XG2010G compatibility boost' not in obj.read_bytes()
queue=root/'target/linux/airoha/patches-6.18'
assert not list(queue.glob('999*overclock*')) and not list(queue.glob('936*pll*')) and not list(queue.glob('937*pll*'))
images=list((root/'bin/targets/airoha/an7581').glob('*gemtek_xg2010g*sysupgrade*.itb'));assert len(images)==1
nodes=fit.board_from_fit(images[0]);assert b'gemtek,xg2010g' in nodes['/']['compatible'].split(b'\0')
cpus=[p for n,p in nodes.items() if re.match(r'^/cpus/cpu@[^/]+$',n)];assert len(cpus)==4
phandles={fit.cells(p['phandle'])[0]:n for n,p in nodes.items() if 'phandle' in p}
tables={fit.cells(p['operating-points-v2'])[0] for p in cpus};assert len(tables)==1
table=phandles[next(iter(tables))];freqs=[]
for n,p in nodes.items():
 if n.startswith(table+'/') and 'opp-hz' in p:
  hz=fit.cells(p['opp-hz']);mhz=((hz[0]<<32)|hz[1])//1000000
  state=fit.cells(nodes[phandles[fit.cells(p['required-opps'])[0]]]['opp-level'])[0]
  assert mhz==500+50*state and state<=14 and 'turbo-mode' not in p
  freqs.append(mhz)
assert sorted(freqs)==list(range(500,1201,50))
assert all('gemtek,1400mhz-boost' not in p and 'airoha,force-direct-pll' not in p for p in nodes.values())
roots=list((root/'build_dir').glob('target-*/root-airoha'));assert len(roots)==1;installed=roots[0]
meta=json.loads((installed/'etc/xg2010g-cpu-boost-source.json').read_text());assert meta['mode']=='stock' and meta['overclock'] is False and meta['maximum_kHz']==1200000
policy=(installed/'usr/libexec/xg2010g-cpu-policy').read_text();assert '1400000' not in policy and 'capable() { echo 0; }' in policy
rpc=(installed/'usr/libexec/rpcd/luci.airoha_npu').read_text();assert 'xg2010g-cpu-policy set-max' in rpc
assert not re.search(r'\bdevmem\s+0x1(?:fa20|efbe)[0-9a-f]+\s+32\s',rpc)
print('Stock BL31 driver/object, four-core 500–1200MHz FIT OPPs and runtime verified; no CPU boost patch')
