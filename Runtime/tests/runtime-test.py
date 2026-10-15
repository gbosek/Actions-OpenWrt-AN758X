#!/usr/bin/env python3
"""Exercise CPU failure semantics, full PPE export and family-aware routing."""
from pathlib import Path
import importlib.util, json, os, shutil, subprocess, sys, tempfile

repo=Path(__file__).resolve().parents[2]
scripts=repo/('scripts' if (repo/'scripts/select-npu.py').exists() else 'Scripts')
runtime=repo/'Runtime'

def run(argv, **kw):
    result=subprocess.run(argv, text=True, capture_output=True, **kw)
    assert result.returncode==0,(argv,result.returncode,result.stdout[-1000:],result.stderr[-2000:])
    return result.stdout

with tempfile.TemporaryDirectory(prefix='xg-runtime-test-') as temp:
 p=Path(temp)
 # Deliberately unequal IRQ/softirq and guest values. SYS must include both
 # interrupt classes and total time must not count guest twice.
 a=p/'first';b=p/'second';cache=p/'cpu-cache.json'
 first='cpu 100 0 50 800 20 10 20 0 100 0\n'
 second='cpu 120 0 60 850 20 20 30 0 120 0\n'
 a.write_text(first+first.replace('cpu ','cpu0 '))
 b.write_text(second+second.replace('cpu ','cpu0 '))
 env=os.environ|{'CPUUSAGE_FIRST':str(a),'CPUUSAGE_SECOND':str(b),'CPUUSAGE_CACHE':str(cache),
                 'CPUUSAGE_PARSER':str(runtime/'root/usr/libexec/xg2010g-cpuusage.awk')}
 sampler=runtime/'root/usr/libexec/xg2010g-cpuusage'
 good=json.loads(run(['sh',str(sampler)],env=env))
 assert not good['stale'] and good['error'] is None
 assert abs(good['busy']-50)<0.001 and abs(good['system']-10)<0.001
 assert good['irq']==10 and good['softirq']==10 and 'SYS(system+IRQ+softirq): 30%' in good['cpuusage']
 assert good['last_success_at'] and good['sample_ms']>=0 and good['cores'][0]['name']=='cpu0'
 b.write_text(a.read_text())
 failed=json.loads(run(['sh',str(sampler)],env=env))
 assert failed['stale'] and failed['error']=='invalid_or_reset_cpu_counters'
 assert failed['last_success_at']==good['last_success_at'] and failed['busy']==good['busy']
 cache.unlink();a.unlink()
 unavailable=json.loads(run(['sh',str(sampler)],env=env))
 assert unavailable['cpuusage']=='Unavailable' and unavailable['error']=='proc_stat_unreadable'
 assert unavailable['last_success_at'] is None and unavailable.get('busy') is None
 # More rows than the normal RPC returns, plus exact uint64 counters.
 entries=p/'entries';cap=p/'config'
 entries.write_text(''.join(f'{i:05x} BND IPv4 5T orig=192.0.2.1:1->198.51.100.1:2 new=192.0.2.1:3->198.51.100.1:4 packets=18446744073709551615 bytes=18446744073709551615\n' for i in range(2100)))
 cap.write_text('npu_attached: 1\nflow_stats_cap: 1\n')
 library=(runtime/'airoha-ppe-snapshot.sh').read_text()
 for old,new in [('/usr/libexec/airoha-deadline.sh',str(runtime/'airoha-deadline.sh')),
                 ('/usr/libexec/airoha-ppe.awk',str(runtime/'airoha-ppe.awk')),
                 ('/sys/kernel/debug/ppe/entries',str(entries)),('/sys/kernel/debug/ppe/config',str(cap)),
                 ('/tmp/xg2010g-ppe',str(p/'ppe'))]:library=library.replace(old,new)
 tool=p/'jsonfilter';tool.write_text("#!/usr/bin/env python3\nimport json,sys\nv=json.load(sys.stdin).get(sys.argv[-1][2:])\nprint(str(v).lower() if isinstance(v,bool) else v if v is not None else '')\n");tool.chmod(0o755)
 fixture_env=os.environ|{'PATH':str(p)+':'+os.environ['PATH']}
 def snapshot(command):return json.loads(run(['bash','-c',library+'\n'+command],env=fixture_env))
 partial=snapshot('get_ppe_entries')
 assert partial['total']==2100 and len(partial['entries'])==1024 and partial['truncated']
 full=snapshot('get_ppe_export')
 assert full['total']==2100 and len(full['entries'])==128 and full['has_more'] is True
 assert full['entries'][0]['bytes']=='18446744073709551615'
 assert full['flow_stats_available'] is True and full['snapshot_atomic'] is False and full['captured_at']>0
 original=entries.read_text();entries.write_text('')
 all_rows=full['entries'];page=full
 while page['has_more']:
  page=snapshot('_ppe_export_page '+full['export_id']+' '+str(page['next_offset']))
  assert page['export_id']==full['export_id'] and page['captured_at']==full['captured_at'] and page['total']==2100
  all_rows+=page['entries']
 assert len(all_rows)==2100 and len({x['index'] for x in all_rows})==2100
 assert not (p/('ppe-export.'+full['export_id'])).exists(), 'Completed snapshot not released'
 entries.write_text(original)
 assert snapshot('_ppe_export_page ../../etc 0')['error']=='invalid_snapshot'
 assert snapshot('_ppe_export_page ABCDEF 1')['error']=='snapshot_expired'
 cap.write_text('flow_stats_cap: 0\n')
 assert snapshot('get_ppe_export')['flow_stats_available'] is False
 cap.write_text('npu_attached: 1\n')
 assert snapshot('get_ppe_export')['flow_stats_available'] is None
 entries.unlink()
 assert snapshot('get_ppe_export')['error']=='ppe_read_failed_or_timeout'
 # LuCI function: a structured failure must retain its real error, while a
 # corrupt/empty helper reply must use a valid cached sample or explicit N/A.
 ucode=os.environ.get('UCODE') or shutil.which('ucode')
 if not ucode:
  candidates=[Path('/home/bosek/ponwrt/staging_dir/hostpkg/bin/ucode')]
  ucode=next((str(x) for x in candidates if x.exists()),None)
 if ucode:
  spec=importlib.util.spec_from_file_location('cpu_cores',scripts/'cpu_cores.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  for value in (good,failed,unavailable):
   program='let sample='+json.dumps(json.dumps(value))+';\nlet popen=function(){return {read:function(){return sample;},close:function(){return 0;}};};\nlet readfile=function(){return null;};\nlet api={'+module.RPC+'};\nprintf("%J\\n",api.getCPUUsage.call());\n'
   f=p/'rpc.uc';f.write_text(program)
   actual=json.loads(run([ucode,str(f)]))
   assert actual==value,('CPU RPC changed failure evidence',actual,value)
  print('PASS: ucode CPU RPC retains structured failures')
 else:print('SKIP: ucode runtime unavailable; CPU shell/AWK exercised')
print('PASS: CPU accounting/cache/failure, >1024-row complete PPE export, uint64 counters and runtime capability')
