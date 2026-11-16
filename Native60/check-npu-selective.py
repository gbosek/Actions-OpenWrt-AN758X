#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib,subprocess
P=Path(__file__).resolve().parent;S=Path(sys.argv[1]);kernels=list((S/'build_dir').glob('target-*/linux-airoha_an7581/linux-6.18.60'));assert len(kernels)==1
K=kernels[0];driver=K/'drivers/net/ethernet/airoha';meta=json.loads((P/'npu-selective-source.json').read_text())
expected=json.loads((P/'prepared-sources.json').read_text());p=driver/'airoha_ppe.c';assert hashlib.sha256(p.read_bytes()).hexdigest()==expected['drivers/net/ethernet/airoha/airoha_ppe.c']
obj=driver/'airoha_ppe.o';b=obj.read_bytes();assert b[:4]==b'\x7fELF' and int.from_bytes(b[18:20],'little')==183
assert b'PPPoE session/peer/VLAN has no exact lower device' in b
report=S/'bin/targets/airoha/an7581/NPU-SELECTIVE-VERIFICATION.json'
subprocess.run([sys.executable,str(P/'tests/npu-selective-test.py'),str(K),'--report',str(report)],check=True)
r=json.loads(report.read_text());r.update({'patches':meta['selected_patches'],'driver_object_sha256':hashlib.sha256(b).hexdigest(),'hardware_tested':False})
report.write_text(json.dumps(r,indent=2)+'\n')
print('PASS actual compiled PPE source/object and session-path regressions')
