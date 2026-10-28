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
  assert release.isdigit() and release=={'naoki':'912','luanmuc':'105'}[variant], 'APK revision must match the reviewed adapter'
  if variant=='naoki':
   make=(app/'Makefile').read_text()
   body=re.search(r'^define Package/\$\(LUCI_NAME\)/install\n(.*?)^endef',make,re.M|re.S).group(1)
   macro=re.search(r'^define Npu/install-exec\n.*?^endef',make,re.M|re.S).group(0)
   stage=root/'installed';harness=root/'install.mk'
   harness.write_text('INSTALL_DIR:=install -d -m 0755\nINSTALL_BIN:=install -m 0755\nINSTALL_DATA:=install -m 0644\n'+macro+'\ndefine Install\n'+body+'endef\n.PHONY: install\ninstall:\n\t$(call Install,'+str(stage)+')\n')
   subprocess.run(['make','-s','-f',str(harness),'-C',str(app),'install'],check=True)
   for rel in ('usr/libexec/airoha-ppe-snapshot.sh','usr/libexec/airoha-deadline.sh','usr/libexec/rpcd/luci.airoha_npu','etc/init.d/airoha-npu'):
    assert (stage/rel).is_file() and (stage/rel).stat().st_mode&0o111, 'Actual install recipe omitted '+rel
   for rel in ('etc/init.d/npu-jitter','usr/libexec/npu-jitter-daemon','etc/rc.d/S89airoha-npu'):
    assert not (stage/rel).exists(), 'Removed automatic task was reinstalled: '+rel
  rpc=app/'root/usr/libexec/rpcd/luci.airoha_npu';s=rpc.read_text()
  subprocess.run(['sh','-n',str(rpc)],check=True)
  for js in app.rglob('*.js'):subprocess.run(['node','--check',str(js)],check=True)
  assert not re.search(r'\bdevmem\s+0x1(?:fa20|efbe)[0-9a-f]+\s+32\s',s)
  assert 'xg2010g-cpu-policy set-max' in s and 'xg2010g-cpu-policy set-governor' in s
  # Verify appended status fields preserve a nested upstream JSON response.
  wrapper=re.search(r'^get_status\(\) \{.*?^\}',s,re.M|re.S).group()
  helper=root/'policy';helper.write_text('#!/bin/sh\ncase "$1" in cap) echo 1;; backend) echo kernel-pll;; esac\n');helper.chmod(0o755)
  code="upstream_get_status() { echo '"+json.dumps({'cpu':{'freq':500},'flows':[]})+"'; }\n"+wrapper.replace('/usr/libexec/xg2010g-cpu-policy',str(helper))+'\nget_status\n'
  out=subprocess.run(['sh','-c',code],capture_output=True,text=True,check=True)
  status=json.loads(out.stdout);assert status['boost_capable']==1 and status['boost_backend']=='kernel-pll' and status['cpu']['freq']==500 and status['flows']==[]
  if variant=='luanmuc':
   js=(app/'htdocs/luci-static/resources/view/airoha_npu/status.js').read_text()
   assert "'max':'1400'" in js and 'Governor locked to performance' not in js and 'r.actual_mhz' not in js
 print('PASS: exclusive NPU providers, shared CPU controls, JSON capability fields and shell/JS syntax')
