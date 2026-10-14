from pathlib import Path
import tempfile,subprocess,os,json,shutil
script=Path(__file__).resolve().parents[1] / 'runtime/xg2010g-cpu-policy'
with tempfile.TemporaryDirectory(prefix='cpu-policy-test-') as d:
 root=Path(d);policy=root/'cpu/policy0';policy.mkdir(parents=True);device=root/'platform/cpufreq';device.mkdir(parents=True)
 (root/'board').write_text('gemtek,xg2010g\n');(root/'cpu/boost').write_text('0\n')
 values={'scaling_governor':'powersave','scaling_available_governors':'ondemand performance powersave','scaling_min_freq':'1400000','scaling_max_freq':'1400000','scaling_available_frequencies':'500000 550000 600000 650000 700000 750000 800000 850000 900000 950000 1000000 1050000 1100000 1150000 1200000','scaling_boost_frequencies':'1400000'}
 for name,value in values.items():(policy/name).write_text(value+'\n')
 (device/'boost_capable').write_text('1\n');(device/'boost_backend').write_text('kernel-pll\n')
 config={'cpufreq.cpufreq':'cpufreq','cpufreq.global':'global','cpufreq.cpufreq.governor0':'ondemand','cpufreq.cpufreq.minfreq0':'500000','cpufreq.cpufreq.maxfreq0':'1400000'}
 (root/'config.json').write_text(json.dumps(config))
 uci=root/'uci';uci.write_text('''#!/usr/bin/python3
import os,json,sys
from pathlib import Path
p=Path(os.environ['XG_TEST_CONFIG']);data=json.loads(p.read_text());args=[x for x in sys.argv[1:] if x!='-q']
if args[0]=='get':
 if args[1] not in data:sys.exit(1)
 print(data[args[1]])
elif args[0]=='set':
 key,value=args[1].split('=',1);data[key]=value;p.write_text(json.dumps(data))
elif args[0]=='commit':pass
else:sys.exit(1)
''');uci.chmod(0o755)
 env=dict(os.environ,XG_CPU_ROOT=str(root/'cpu'),XG_PLATFORM_ROOT=str(root/'platform'),XG_BOARD_FILE=str(root/'board'),XG_UCI=str(uci),XG_TEST_CONFIG=str(root/'config.json'))
 def run(*args,ok=True):
  r=subprocess.run(['sh',str(script),*args],env=env,text=True,capture_output=True)
  assert (r.returncode==0)==ok,(args,r.returncode,r.stdout,r.stderr)
  return r
 run('apply');assert (policy/'scaling_min_freq').read_text().strip()=='500000';assert (policy/'scaling_max_freq').read_text().strip()=='1400000';assert (policy/'scaling_governor').read_text().strip()=='ondemand';assert (root/'cpu/boost').read_text().strip()=='1'
 assert '1400000' in run('frequencies').stdout
 # CPU controls save a ceiling without changing the ondemand governor.
 assert json.loads(run('set-max','1400000').stdout)['result']=='ok'
 assert (policy/'scaling_governor').read_text().strip()=='ondemand'
 assert 'error' in json.loads(run('set-max','1500000',ok=False).stdout)
 assert 'error' in json.loads(run('set-max','1250000',ok=False).stdout)
 run('set-max','1200000');assert (root/'cpu/boost').read_text().strip()=='0'
 run('set-max','1400000');assert (root/'cpu/boost').read_text().strip()=='1'
 # A kernel fault or unavailable backend removes boost and bounds the policy.
 (device/'boost_capable').write_text('0\n');(device/'boost_backend').write_text('unavailable\n')
 run('apply');assert (policy/'scaling_max_freq').read_text().strip()=='1200000';assert (root/'cpu/boost').read_text().strip()=='0';assert '1400000' not in run('frequencies').stdout
 assert 'error' in json.loads(run('set-max','1400000',ok=False).stdout)
 assert json.loads((root/'config.json').read_text())['cpufreq.cpufreq.maxfreq0']=='1200000'
 # Invalid user input is rejected by the available-governor list.
 assert 'error' in json.loads(run('set-governor','invalid',ok=False).stdout)
 (root/'board').write_text('other,board\n');run('apply');assert 'error' in json.loads(run('set-max','1200000',ok=False).stdout)
 print('PASS: dynamic 500–1400 range, unchanged governor, ceiling persistence, boost enable/disable, unsupported frequencies, fault fallback to1200 and board guard')
