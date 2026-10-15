#!/usr/bin/env python3
"""Run the actual route guard against a stateful ip/ubus/netifd fixture."""
from pathlib import Path
import json, os, subprocess, tempfile
repo=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='xg-routes-test-') as temp:
 p=Path(temp);bin=p/'bin';bin.mkdir();state=p/'run';state.mkdir();(state/'mwan4').mkdir()
 (p/'board').write_text('gemtek,xg2010g\n')
 rules={'4':['9009: from all to 203.0.113.8 lookup 10'],
        '6':['10050: from 2001:db8:1::/64 lookup main','1001: from all iif pppoe-wan lookup 1',
             '2001: from all fwmark 0x100/0x3f00 lookup 1','3001: from all fwmark 0x100/0x3f00 unreachable']}
 (p/'rules.json').write_text(json.dumps(rules))
 (p/'online.json').write_text(json.dumps({'wan':True,'wanb':True,'wan_6':True,'wanb_6':True}))
 (p/'resolv').write_text('# Interface wan\nnameserver 223.5.5.5\nnameserver 2400:3200::1\n# Interface wanb_6\nnameserver 2400:3200:baba::1\n')
 (p/'functions').write_text('''config_load() { :; }
config_get() {
 local value="$4"
 case "$2:$3" in globals:mmx_mask) value=0x3f00;; *:enabled) value=1;; *_6:family) value=ipv6;; *:family) value=ipv4;; esac
 eval "$1=\\\"$value\\\""
}
config_foreach() { "$1" wan; "$1" wanb; "$1" wan_6; "$1" wanb_6; }
''')
 stub='''#!/usr/bin/env python3
import json,sys,os
from pathlib import Path
p=Path(os.environ['FIXTURE']);args=sys.argv[1:];cmd=Path(sys.argv[0]).name
if cmd=='ip':
 f=args[0][1:];a=args[1:];file=p/'rules.json';rules=json.loads(file.read_text())
 if a[:2]==['route','show']:
  tid=a[-1]
  if f=='4' and tid in ('1','2') or f=='6' and tid in ('3','4'):print('default dev pppoe-wan')
 elif a[:2]==['rule','show']:print('\\n'.join(rules[f]))
 elif a[0]=='rule':
  pref=a[a.index('pref')+1];spec=' '.join(a[a.index('pref')+2:]);line=pref+': from all '+spec
  if a[1]=='add':rules[f].append(line)
  elif a[1]=='del':
   if line not in rules[f]:sys.exit(2)
   rules[f].remove(line)
  file.write_text(json.dumps(rules))
 else:sys.exit(3)
elif cmd=='ubus':
 iface=args[1].split('.')[2];online=json.loads((p/'online.json').read_text())
 print(json.dumps({'up':online[iface],'l3_device':'pppoe-'+iface.removesuffix('_6')}))
elif cmd=='jsonfilter':
 obj=json.load(sys.stdin);field=args[-1][2:];value=obj.get(field)
 print(str(value).lower() if isinstance(value,bool) else value or '')
'''
 for name in ('ip','ubus','jsonfilter'):
  path=bin/name;path.write_text(stub);path.chmod(0o755)
 text=(repo/'Runtime/root/usr/bin/mwan4-rule-guard.sh').read_text()
 for old,new in [('/tmp/sysinfo/board_name',str(p/'board')),('/lib/functions.sh',str(p/'functions')),
                 ('/var/run',str(state)),('/tmp/resolv.conf.d/resolv.conf.auto',str(p/'resolv'))]:text=text.replace(old,new)
 guard=p/'guard';guard.write_text(text)
 env=os.environ|{'PATH':str(bin)+':'+os.environ['PATH'],'FIXTURE':str(p)}
 def call(*args):
  result=subprocess.run(['sh',str(guard),*args],env=env,capture_output=True,text=True)
  assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
  return result.stdout
 plan=call('--plan');assert 'lookup 3' in plan and 'lookup 4' in plan
 call('--routes-only');current=json.loads((p/'rules.json').read_text())
 assert '9001: from all to 223.5.5.5 lookup 1' in current['4']
 assert '9101: from all to 2400:3200::1 lookup 3' in current['6']
 assert '9102: from all to 2400:3200:baba::1 lookup 4' in current['6']
 assert not any('lookup 1' in x for x in current['6'])
 assert '10050: from 2001:db8:1::/64 lookup main' in current['6']
 assert call('--plan').strip()==''
 before=(p/'rules.json').read_bytes();call('--routes-only');assert before==(p/'rules.json').read_bytes()
 # A redial/down event withdraws only the DNS entries owned by this script.
 (p/'online.json').write_text(json.dumps({'wan':False,'wanb':True,'wan_6':False,'wanb_6':True}))
 call('--routes-only');current=json.loads((p/'rules.json').read_text())
 assert not any('to 2400:3200::1' in x for x in current['6'])
 assert '9101: from all to 2400:3200:baba::1 lookup 4' in current['6']
 call('--cleanup');current=json.loads((p/'rules.json').read_text())
 assert not any('to 2400:' in x for x in current['6'])
 assert '9009: from all to 203.0.113.8 lookup 10' in current['4']
 assert '10050: from 2001:db8:1::/64 lookup main' in current['6']
 (state/'mwan4').rmdir();call('--routes-only')
 assert current==json.loads((p/'rules.json').read_text()),'Stopped MWAN4 was resurrected'
print('PASS: family table 1/2 vs 3/4, DNS pinning, idempotence, down-event reconciliation, stop cleanup, preserved source-prefix/user rules')
