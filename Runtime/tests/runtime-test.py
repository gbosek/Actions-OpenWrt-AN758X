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
 assert full['counter_schema']==2 and full['boot_id'] and full['captured_uptime']>0
 assert full['entries'][0]['counter_status']=='reported_bound_slot'
 assert full['entries'][0]['raw']['bytes']=='18446744073709551615'
 assert full['flow_stats_available'] is True and full['snapshot_atomic'] is False and full['captured_at']>0
 original=entries.read_text();entries.write_text('')
 all_rows=full['entries'];page=full
 while page['has_more']:
  page=snapshot('_ppe_export_page '+full['export_id']+' '+str(page['next_offset']))
  assert page['export_id']==full['export_id'] and page['captured_at']==full['captured_at'] and page['total']==2100
  assert page['boot_id']==full['boot_id'] and page['captured_uptime']==full['captured_uptime']
  all_rows+=page['entries']
 assert len(all_rows)==2100 and len({x['index'] for x in all_rows})==2100
 assert not (p/('ppe-export.'+full['export_id'])).exists(), 'Completed snapshot not released'
 entries.write_text(original)
 assert snapshot('_ppe_export_page ../../etc 0')['error']=='invalid_snapshot'
 assert snapshot('_ppe_export_page ABCDEF 1')['error']=='snapshot_expired'
 cap.write_text('flow_stats_cap: 0\n')
 disabled=snapshot('get_ppe_export')
 assert disabled['flow_stats_available'] is False and disabled['entries'][0]['bytes'] is None
 assert disabled['entries'][0]['counter_status']=='driver_disabled'
 cap.write_text('npu_attached: 1\n')
 unknown=snapshot('get_ppe_export')
 assert unknown['flow_stats_available'] is None and unknown['entries'][0]['packets'] is None
 assert unknown['entries'][0]['counter_status']=='driver_unreported'
 # A slot reused for an unbound key may still expose its old NPU counters.
 # Preserve the raw evidence without attributing it to the new connection.
 cap.write_text('flow_stats_cap: 1\n')
 examples=[
  '00308 UNB IPv4 5T orig=198.18.0.4:443->192.168.10.66:56392 new=9.8.7.6:1->5.4.3.2:2 vlan=65535,1 ib1=10000000 ib2=deadbeef data=12345678 packets=441 bytes=642437',
  '00309 FIN IPv4 5T orig=192.168.10.66:1->192.0.2.1:2 packets=8 bytes=900',
  '0030a BND L2B eth=02:00:00:00:00:01->02:00:00:00:00:02 vlan=0,0 packets=0 bytes=0',
  '0030b BND IPv4 5T orig=192.0.2.1:443->10.90.149.142:12345 new=192.0.2.1:443->192.168.10.2:12345 packets=9 bytes=9876',
  '0030c BND IPv4 5T orig=192.168.10.66:12345->198.18.0.26:443 new=192.168.10.66:12345->198.18.0.26:443 packets=10 bytes=12345',
  '0030d BND IPv6 5T orig=2001:db8::1:1->2001:db8::2:2 packets=0 bytes=0',
 ]
 entries.write_text('\n'.join(examples)+'\n')
 checked=snapshot('get_ppe_export'); unb,fin,l2,inbound,bridge,zero=checked['entries']
 assert checked['bound']==4 and checked['unbound']==1 and checked['finished']==1
 assert unb['packets'] is None and unb['bytes'] is None and unb['counter_status']=='not_bound'
 assert unb['new_flow'] is None and unb['vlan'] is None and unb['raw']['new_flow']=='9.8.7.6:1->5.4.3.2:2'
 assert unb['raw']['packets']=='441' and unb['ib1']=='10000000' and unb['ib2']=='deadbeef' and unb['data']=='12345678'
 assert fin['packets'] is None and fin['raw']['packets']=='8'
 assert l2['counter_status']=='unsupported_l2_counter' and l2['packets'] is None and l2['raw']['packets']=='0'
 assert inbound['packets']=='9' and bridge['bytes']=='12345' and zero['bytes']=='0'
 examples[0]='00308 UNB IPv6 5T orig=2001:db8::1:1->2001:db8::2:2 packets=441 bytes=642437'
 entries.write_text('\n'.join(examples)+'\n')
 reused=snapshot('get_ppe_export')['entries'][0]
 assert reused['orig']!=unb['orig'] and reused['raw']['bytes']==unb['raw']['bytes']
 assert reused['bytes'] is None, 'Old slot statistics attributed to a different current flow'
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
