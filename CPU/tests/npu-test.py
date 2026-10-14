#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess,json,re
repo=Path(__file__).resolve().parents[2]
scripts=repo/('scripts' if (repo/'scripts/select-npu.py').exists() else 'Scripts')
with tempfile.TemporaryDirectory(prefix='xg2010g-npu-test-') as d:
 root=Path(d);(root/'target/linux/airoha').mkdir(parents=True)
 for variant in ('naoki','luanmuc'):
  subprocess.run(['python3',str(scripts/'select-npu.py'),d,'--variant',variant],check=True)
  apps=list((root/'package/custom').glob('luci-app-airoha*'));assert len(apps)==1
  app=apps[0]
  release=re.search(r'^PKG_RELEASE:=(.+)$',(app/'Makefile').read_text(),re.M).group(1)
  assert release.isdigit() and release=={'naoki':'901','luanmuc':'101'}[variant], 'APK revision must be an integer'
  rpc=app/'root/usr/libexec/rpcd/luci.airoha_npu';s=rpc.read_text()
  subprocess.run(['sh','-n',str(rpc)],check=True)
  for js in app.rglob('*.js'):subprocess.run(['node','--check',str(js)],check=True)
  assert not re.search(r'\bdevmem\s+0x1(?:fa20|efbe)[0-9a-f]+\s+32\s',s)
  assert 'xg2010g-cpu-policy set-max' in s and 'xg2010g-cpu-policy set-governor' in s
  # Verify appended status fields preserve a nested upstream JSON response.
  wrapper=re.search(r'^get_status\(\) \{.*?^\}',s,re.M|re.S).group()
  helper=root/'policy';helper.write_text('#!/bin/sh\ncase "$1" in cap) echo 0;; backend) echo bl31;; esac\n');helper.chmod(0o755)
  code="upstream_get_status() { echo '"+json.dumps({'cpu':{'freq':500},'flows':[]})+"'; }\n"+wrapper.replace('/usr/libexec/xg2010g-cpu-policy',str(helper))+'\nget_status\n'
  out=subprocess.run(['sh','-c',code],capture_output=True,text=True,check=True)
  status=json.loads(out.stdout);assert status['boost_capable']==0 and status['boost_backend']=='bl31' and status['cpu']['freq']==500 and status['flows']==[]
  if variant=='luanmuc':
   js=(app/'htdocs/luci-static/resources/view/airoha_npu/status.js').read_text()
   assert "'max':'1200'" in js and 'Governor locked to performance' not in js and 'r.actual_mhz' not in js and 'renderOcControls())' not in js
 print('PASS: exclusive NPU providers, shared CPU controls, JSON capability fields and shell/JS syntax')
