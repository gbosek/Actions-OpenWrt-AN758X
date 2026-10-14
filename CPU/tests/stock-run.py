#!/usr/bin/env python3
"""Check stock integration against exact upstream fixtures and CPU ceilings."""
from pathlib import Path
import importlib.util,json,os,shutil,subprocess,tempfile
repo=Path(__file__).resolve().parents[2];scripts=repo/('scripts' if (repo/'scripts/apply-stock-cpu.py').exists() else 'Scripts')
for flavor in ['pon','ci']:
 with tempfile.TemporaryDirectory() as d:
  root=Path(d);fixtures=repo/'CPU/tests/fixtures'
  for source,target in [(flavor+'-board.dts','target/linux/airoha/dts/an7581-gemtek-xg2010g.dts'),(flavor+'-config','target/linux/airoha/an7581/config-6.18'),(flavor+'-cpufreq-Makefile','package/emortal/cpufreq/Makefile')]:
   f=root/target;f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(fixtures/source,f)
  queue=root/'target/linux/airoha/patches-6.18';queue.mkdir();(root/'package/emortal/cpufreq/files').mkdir()
  (root/'package/emortal/cpufreq/files/cpufreq.config').write_text("config cpufreq 'cpufreq'\n")
  board=root/'target/linux/airoha/dts/an7581-gemtek-xg2010g.dts';before=board.read_bytes()
  for _ in range(2):subprocess.run(['python3',str(scripts/'apply-stock-cpu.py'),d],check=True)
  assert board.read_bytes()==before and not list(queue.iterdir())
  make=(root/'package/emortal/cpufreq/Makefile').read_text();assert make.count('$(1)/usr/libexec/xg2010g-cpu-policy')==1 and '\n\t$(INSTALL_DIR) $(1)/usr/libexec\n' in make
  subprocess.run(['python3',str(repo/'CPU/tests/cpufreq-install-test.py'),str(root/'package/emortal/cpufreq/Makefile')],check=True)
  policy=root/'cpu/policy0';policy.mkdir(parents=True)
  values={'scaling_governor':'powersave','scaling_available_governors':'ondemand performance powersave','scaling_min_freq':'500000','scaling_max_freq':'1200000','scaling_available_frequencies':'500000 600000 800000 1000000 1200000'}
  for name,value in values.items():(policy/name).write_text(value+'\n')
  (root/'board').write_text('gemtek,xg2010g\n');cfg=root/'config.json';cfg.write_text(json.dumps({'cpufreq.cpufreq':'cpufreq','cpufreq.global':'global','cpufreq.cpufreq.governor0':'ondemand','cpufreq.cpufreq.minfreq0':'500000','cpufreq.cpufreq.maxfreq0':'1200000'}))
  uci=root/'uci';uci.write_text('''#!/usr/bin/python3
import os,json,sys
from pathlib import Path
p=Path(os.environ['TEST_UCI']);data=json.loads(p.read_text());args=[x for x in sys.argv[1:] if x!='-q']
if args[0]=='get':
 if args[1] not in data:sys.exit(1)
 print(data[args[1]])
elif args[0]=='set':
 key,value=args[1].split('=',1);data[key]=value;p.write_text(json.dumps(data))
elif args[0]=='commit':pass
else:sys.exit(1)
''');uci.chmod(0o755)
  env=dict(os.environ,XG_CPU_ROOT=str(root/'cpu'),XG_PLATFORM_ROOT=str(root/'platform'),XG_BOARD_FILE=str(root/'board'),XG_UCI=str(uci),TEST_UCI=str(cfg))
  helper=repo/'CPU/runtime/xg2010g-cpu-policy'
  def run(*args,ok=True):
   r=subprocess.run(['sh',str(helper),*args],env=env,capture_output=True,text=True);assert (r.returncode==0)==ok,(args,r.stdout,r.stderr);return r
  run('apply');assert (policy/'scaling_governor').read_text().strip()=='ondemand'
  run('set-max','1200000');assert (policy/'scaling_min_freq').read_text().strip()=='500000'
  run('set-max','1400000',ok=False);run('set-max','1500000',ok=False)
  assert run('cap').stdout.strip()=='0' and run('backend').stdout.strip()=='bl31'
  assert '1400000' not in run('frequencies').stdout
subprocess.run(['python3',str(repo/'CPU/tests/npu-test.py')],check=True)
spec=importlib.util.spec_from_file_location('queue',scripts/'wait-for-boost.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert not module.ready(None) and not module.ready({'status':'in_progress','conclusion':None}) and not module.ready({'status':'completed','conclusion':'failure'})
assert module.ready({'status':'completed','conclusion':'success'})
assert module.choose_run('current',[{'id':1,'head_sha':'old','event':'push','path':'x.yml','status':'completed','conclusion':'success'}],'x.yml') is None
assert not all(module.ready(r) for r in [{'status':'completed','conclusion':'success'}]*3+[{'status':'in_progress','conclusion':None}])
print('PASS: unmodified stock DTS/driver queue, dynamic 500–1200 policy, rejected overclock settings, NPU variants and four-build dependency gate')
subprocess.run(['python3',str(repo/'CPU/tests/pon-selection-test.py')],check=True)
