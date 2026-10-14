#!/usr/bin/env python3
"""Use exact pinned upstream bytes, including EOF, to check boost installation."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tempfile
repo=Path(__file__).resolve().parents[2]
scripts=repo/('scripts' if (repo/'scripts/apply-compatible-boost.py').exists() else 'Scripts')
fixtures=repo/'CPU/tests/fixtures'
manifest=json.loads((fixtures/'SOURCE.json').read_text())
for filename,meta in manifest.items():
 assert hashlib.sha256((fixtures/filename).read_bytes()).hexdigest()==meta['sha256'],filename
for flavor,version in [('pon','6.18.52'),('ci','6.18.54')]:
 with tempfile.TemporaryDirectory(prefix='xg2010g-install-test-') as d:
  root=Path(d)
  board=root/'target/linux/airoha/dts/an7581-gemtek-xg2010g.dts'
  board.parent.mkdir(parents=True)
  shutil.copyfile(fixtures/(flavor+'-board.dts'),board)
  # This exact EOF caused the old patch to fail; do not serialize/reformat it.
  assert board.read_bytes().endswith(b'};\n') and not board.read_bytes().endswith(b'};\n\n')
  cfg=root/'target/linux/airoha/an7581/config-6.18';cfg.parent.mkdir(parents=True)
  shutil.copyfile(fixtures/(flavor+'-config'),cfg)
  queue=root/'target/linux/airoha/patches-6.18';queue.mkdir()
  make=root/'package/emortal/cpufreq/Makefile';make.parent.mkdir(parents=True)
  (make.parent/'files').mkdir()
  shutil.copyfile(fixtures/(flavor+'-cpufreq-Makefile'),make)
  script=scripts/'apply-compatible-boost.py'
  subprocess.run(['python3',str(script),d],check=True,stdout=subprocess.DEVNULL)
  first=board.read_bytes()
  subprocess.run(['python3',str(script),d],check=True,stdout=subprocess.DEVNULL)
  assert board.read_bytes()==first,'Repeated DTS application changed source'
  assert first.count(b'gemtek,1400mhz-boost')==1 and first.count(b'opp-1400000000')==1
  assert b'bootargs = "console=ttyS0,115200 earlycon cpufreq.default_governor=powersave";' in first
  assert make.read_text().count('$(1)/usr/libexec/xg2010g-cpu-policy')==1
  # Do not auto-reverse an applied patch or conceal incompatible board source.
  incompatible=first.replace(b'cpufreq.default_governor=powersave',b'cpufreq.default_governor=performance')
  board.write_bytes(incompatible)
  failed=subprocess.run(['python3',str(script),d],capture_output=True,text=True)
  assert failed.returncode!=0 and 'Hunk #1 FAILED' in failed.stderr
  assert board.read_bytes()==incompatible
  board.write_bytes(first)
  for name in ['cpufreq.init','cpufreq.uci','xg2010g-cpu-policy']:
   installed=make.parent/'files'/name
   assert installed.read_bytes()==(repo/'CPU/runtime'/name).read_bytes() and installed.stat().st_mode&0o111
  c=root/'drivers/pmdomain/mediatek/airoha-cpu-pmdomain.c';c.parent.mkdir(parents=True)
  shutil.copyfile(fixtures/('driver-'+version+'.c'),c)
  for patch in [fixtures/'221-02-pmdomain-airoha-Add-AN7583-cpufreq-compatible.patch',queue/'999-xg2010g-bl31-compatible-overclock.patch']:
   subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',d,'-i',str(patch)],check=True,stdout=subprocess.DEVNULL)
  assert c.read_text().count('airoha,an7583-cpufreq')==1
  assert 'xg2010g_boost_set_state' in c.read_text()
  assert (c.parent/'xg2010g-cpu-boost.h').is_file()
  metadata=json.loads((root/'files/etc/xg2010g-cpu-boost-source.json').read_text())
  assert metadata['source_dts_patch_sha256']==hashlib.sha256((repo/'source-patches/airoha'/metadata['source_dts_patch']).read_bytes()).hexdigest()
  print('PASS: exact pinned '+flavor+' source EOF, installation/reapplication and Linux '+version+' kernel patch')
