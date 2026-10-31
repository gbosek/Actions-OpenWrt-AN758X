#!/usr/bin/env python3
"""Check exact final patch/package sources and native stable de-duplication."""
from pathlib import Path
import hashlib,json,re,sys
R=Path(__file__).resolve().parents[1];S=Path(sys.argv[1]).resolve();m=json.loads((R/'Kernel60/SOURCE.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for r in m['files']:assert sha(S/r['path'])==r['after_sha256'],r['path']
actual_queue=[]
for folder in ['generic/backport-6.18','generic/pending-6.18','generic/hack-6.18','airoha/patches-6.18']:
    actual_queue += [{'path':str(p.relative_to(S)),'sha256':sha(p)} for p in sorted((S/'target/linux'/folder).glob('*.patch'))]
assert actual_queue==m['patch_queue'],'Kernel patch queue differs from the clean zero-fuzz replay'
kernels=[Path(sys.argv[2])] if len(sys.argv)>2 else [p.parent for p in (S/'build_dir').glob('target-*/linux-airoha_an7581/linux-6.18.60/.config')]
assert len(kernels)==1,'Expected exactly one prepared Linux 6.18.60'
K=kernels[0]
for n,v in m['prepared_sources'].items():assert sha(K/n)==v,n
offload=json.loads((R/'Offload/SOURCE.json').read_text())
for n,v in offload['expected_prepared_sources'].items():assert sha(K/n)==v,n
core=(K/'net/netfilter/nf_flow_table_core.c').read_text();off=(K/'net/netfilter/nf_flow_table_offload.c').read_text();path=(K/'net/netfilter/nf_flow_table_path.c').read_text()
assert 'test_bit(NF_FLOW_PENDING, &flow->flags)' in core and 'test_and_set_bit(NF_FLOW_PENDING, &flow->flags)' in off,'Native work/GC synchronization absent'
assert 'if (!info->num_encaps)' in path,'Native/adapted VLAN underflow guard absent'
assert path.count('static int nft_dev_path_info(')==1
assert path.count('static int nft_dev_forward_path(')==1
assert 'port_vlans = 0;' in path
out={'kernel':'6.18.60','status':'passed','source_metadata_sha256':sha(R/'Kernel60/SOURCE.json'),'checked_files':len(m['files']),'prepared_sources':m['prepared_sources'],'scope':'Exact source identity and native-fix checks, not a device validation'}
(S/'KERNEL60-PREPARED-VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS exact Linux6.18.60 final source/package identity and native de-duplication')
