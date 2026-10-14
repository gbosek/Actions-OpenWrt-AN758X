#!/usr/bin/env python3
"""Execute the generated package install recipe, rather than inspecting its text."""
from pathlib import Path
import argparse,re,subprocess,tempfile

def verify_install(makefile):
 makefile=Path(makefile);source=makefile.read_text()
 body=re.search(r'^define Package/cpufreq/install\n(.*?)^endef',source,re.M|re.S).group(1)
 with tempfile.TemporaryDirectory(prefix='xg-cpufreq-install-') as d:
  root=Path(d);stage=root/'rootfs';harness=root/'install.mk'
  harness.write_text('INSTALL_DIR:=install -d -m 0755\nINSTALL_BIN:=install -m 0755\nINSTALL_CONF:=install -m 0600\nCURDIR:='+str(makefile.parent)+'\ndefine Package/cpufreq/install\n'+body+'endef\n.PHONY: install\ninstall:\n\t$(call Package/cpufreq/install,'+str(stage)+')\n')
  subprocess.run(['make','--no-print-directory','-f',str(harness),'install'],check=True,stdout=subprocess.DEVNULL)
  files={'usr/libexec/xg2010g-cpu-policy':'xg2010g-cpu-policy','etc/init.d/cpufreq':'cpufreq.init','etc/uci-defaults/10-cpufreq':'cpufreq.uci'}
  for target,original in files.items():
   installed=stage/target
   assert installed.is_file() and installed.stat().st_mode&0o111,'Missing correctly installed executable '+target
   assert installed.read_bytes()==(makefile.parent/'files'/original).read_bytes(),target
  assert (stage/'etc/config/cpufreq').is_file()
  assert not (stage/'etc/init.d/cpufreq.init').exists()
  assert not (stage/'usr/libexec/xg2010g-cpu-policycpufreq').exists()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('makefile',type=Path);a=p.parse_args();verify_install(a.makefile);print('PASS: actual cpufreq package install recipe produced the canonical helper/init/default paths with executable modes')
