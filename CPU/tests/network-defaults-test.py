#!/usr/bin/env python3
"""Exercise the explicit-start preset without changing retained policies."""
from pathlib import Path
import json, os, subprocess, tempfile

repo = Path(__file__).resolve().parents[2]
source = repo / 'files/usr/libexec/xg2010g-mwan4-preset'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    board = root / 'board'; board.write_text('gemtek,xg2010g\n')
    reference = root / 'reference'; reference.write_text('stock package template\n')
    config = root / 'mwan4'; config.write_bytes(reference.read_bytes())
    state = root / 'uci.json'
    binpath = root / 'bin'; binpath.mkdir()
    uci = binpath / 'uci'
    uci.write_text('''#!/usr/bin/python3
import os,json,sys
from pathlib import Path
p=Path(os.environ['TEST_UCI']);d=json.loads(p.read_text());a=[s for s in sys.argv[1:] if s!='-q'];op=a[0];v=a[1] if len(a)>1 else ''
if op=='get':
 if v not in d:sys.exit(1)
 print(' '.join(d[v]) if isinstance(d[v],list) else d[v])
elif op=='set':
 k,val=v.split('=',1);d[k]=val
elif op=='delete':d.pop(v,None)
elif op=='add_list':
 k,val=v.split('=',1);d.setdefault(k,[]).append(val)
elif op=='rename':
 k,val=v.split('=',1);dest=k.rsplit('.',1)[0]+'.'+val
 for old in list(d):
  if old==k or old.startswith(k+'.'):d[dest+old[len(k):]]=d.pop(old)
elif op=='reorder':d.setdefault('_reorder',[]).append(v)
elif op!='commit':sys.exit(1)
if op!='get':p.write_text(json.dumps(d))
'''); uci.chmod(0o755)
    for name, program in {
        'ubus': '''#!/usr/bin/python3
import json,sys,os
name=sys.argv[2]
dns=[] if os.environ.get('TEST_NO_DNS') else (['240e:1f:1::1','240e:1f:1::33'] if 'wanb' in name else ['2408:8888::8','2408:8899::8'])
print(json.dumps({'dns-server':dns}))
''',
        'jsonfilter': '''#!/usr/bin/python3
import json,sys
print('\\n'.join(json.load(sys.stdin)['dns-server']))
''',
    }.items():
        path=binpath/name;path.write_text(program);path.chmod(0o755)
    script = root / 'defaults'
    script.write_text(source.read_text().replace('/tmp/sysinfo/board_name', str(board)).replace('/usr/share/xg2010g/mwan4-stock.config', str(reference)).replace('/etc/config/mwan4', str(config)))
    env = dict(os.environ, PATH=str(binpath)+':'+os.environ['PATH'], TEST_UCI=str(state))
    def seed():
        return {'network.wan':'interface','network.wan.proto':'pppoe','network.wan.ipv6':'auto','network.wanb':'interface','network.wanb.proto':'pppoe','network.wanb.ipv6':'auto','network.wanb.password':'keep-test-value','network.wanb.device':'unchanged-device','network.wan.dns':['192.0.2.53'],'mwan4.wan.enabled':'1','mwan4.wanb.enabled':'0','mwan4.wan6':'interface','mwan4.wan6.enabled':'0','mwan4.wanb6':'interface','mwan4.wanb6.enabled':'0'}
    def run(data):
        state.write_text(json.dumps(data));subprocess.run(['sh', str(script)],env=env,check=True);return json.loads(state.read_text())
    initial = seed(); data = run(initial)
    assert data['mwan4.wanb.enabled']=='1'
    assert data['mwan4.wan_6.enabled']==data['mwan4.wanb_6.enabled']=='1'
    assert data['network.wan.metric']=='10' and data['network.wanb.metric']=='20'
    assert data['mwan4.wan.track_ip']==['223.5.5.5','119.29.29.29','114.114.114.114']
    assert data['mwan4.wan_6.track_ip']==['2408:8888::8','2408:8899::8']
    assert data['mwan4.wanb_6.track_ip']==['240e:1f:1::1','240e:1f:1::33']
    assert data['mwan4.wan_6.count']==data['mwan4.wanb_6.count']=='3'
    assert data['mwan4.default_rule_v4.enabled']=='1' and data['mwan4.default_rule_v6.enabled']=='0'
    assert data['mwan4.wanb_m1_w3.weight']==data['mwan4.wan_m1_w3.weight']=='1'
    assert data['mwan4.balanced.use_route']==['wan_m1_w3','wanb_m1_w3']
    assert data['_reorder']==['mwan4.wan=1','mwan4.wanb=2','mwan4.wan_6=3','mwan4.wanb_6=4']
    for key in ['network.wanb.password','network.wanb.device','network.wan.dns']:assert data[key]==initial[key]
    initial = seed(); initial['network.wan.metric']='0'; initial['network.wanb.metric']='0'
    data = run(initial); assert data['network.wan.metric']=='10' and data['network.wanb.metric']=='20'
    # A preserved user policy must not be replaced, even when it has the same WAN names.
    config.write_text('saved custom user policy\n');assert run(initial)==initial
    config.write_bytes(reference.read_bytes())
    initial=seed();initial['network.wan.metric']='45';initial['network.wanb.metric']='55';initial['network.wanb.ipv6']='0'
    initial['network.wan6']='interface';initial['network.wan6.proto']='dhcpv6'
    data=run(initial);assert data['network.wan.metric']=='45' and data['network.wanb.metric']=='55'
    assert data['mwan4.wan6.enabled']=='1' and data['mwan4.wanb6.enabled']=='0'
    assert 'mwan4.wanb_6' not in data and 'mwan4.wan_6' not in data
    initial=seed();del initial['network.wanb'];data=run(initial);assert data['mwan4.wanb.enabled']=='0'
    board.write_text('other,board\n');assert run(initial)==initial
    board.write_text('gemtek,xg2010g\n')
    env['TEST_NO_DNS']='1';data=run(seed())
    assert data['mwan4.wan_6.enabled']==data['mwan4.wanb_6.enabled']=='0'
    assert not any(key.startswith('network.') and 'ipv6' in key and value=='0' for key,value in data.items())
print('PASS: fresh dual-WAN defaults, actual IPv6 names, metric/probe preset, retained policies/credentials/devices/DNS and user metrics preserved')
