#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parents[1];S=Path(sys.argv[1]).resolve()
m=json.loads((R/'Maintenance55/SOURCE.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
assert 'LINUX_VERSION-6.18 = .55' in (S/'target/linux/generic/kernel-6.18').read_text()
for x in m['files']:assert sha(S/x['path'])==x['after_sha256'],x['path']
queue=[{'path':str(p.relative_to(S)),'sha256':sha(p)} for d in ['generic/backport-6.18','generic/pending-6.18','generic/hack-6.18','airoha/patches-6.18'] for p in sorted((S/'target/linux'/d).glob('*.patch'))]
assert queue==m['patch_queue'],'Complete .55 patch inventory differs'
found=[Path(sys.argv[2])] if len(sys.argv)>2 else sorted({p.parents[4] for p in (S/'build_dir').glob('target-*/linux-airoha_an7581/linux-6.18.55/drivers/net/ethernet/airoha/airoha_ppe.c')})
assert len(found)==1,f'Expected one prepared .55 kernel, got {len(found)}'
K=found[0]
for n,h in m['prepared_sources'].items():assert sha(K/n)==h,n
assert 'NF_FLOW_HW_PENDING' not in (K/'include/net/netfilter/nf_flow_table.h').read_text()
assert 'test_bit(NF_FLOW_PENDING, &flow->flags)' in (K/'net/netfilter/nf_flow_table_core.c').read_text()
pcs=(K/'drivers/net/pcs/airoha/pcs-airoha-common.c').read_text()
assert pcs.count('index >= priv->data->num_port')==1,'Duplicate PCS index check'
out={'status':'passed','kernel':'6.18.55','prepared_sources':m['prepared_sources'],'patches':len(queue),'hardware_tested':False}
(S/'MAINTENANCE55-PREPARED-VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS .55 kernel identity, exact patch/source hashes and stable flowtable guards')
