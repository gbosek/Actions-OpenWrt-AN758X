#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent;S=Path(sys.argv[1]);kernels=list((S/'build_dir').glob('target-*/linux-airoha_an7581/linux-6.18.60'))
assert len(kernels)==1,kernels
K=kernels[0];expected=json.loads((P/'prepared-sources.json').read_text())
for rel,h in expected.items():
 assert hashlib.sha256((K/rel).read_bytes()).hexdigest()==h,'CI compiled source mismatch: '+rel
 obj=K/rel.replace('.c','.o');assert obj.is_file() and obj.stat().st_size>0,obj
config=(K/'.config').read_text()
for k in ['CONFIG_NET_AIROHA','CONFIG_NET_AIROHA_NPU','CONFIG_NF_FLOW_TABLE','CONFIG_NFT_FLOW_OFFLOAD']:
 assert k+'=y' in config or k+'=m' in config,k
print('PASS exact CI prepared source hashes and eight compiled objects')
