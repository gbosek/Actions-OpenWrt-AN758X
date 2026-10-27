#!/usr/bin/env python3
import os,subprocess,tempfile
from pathlib import Path
repo=Path(__file__).resolve().parents[2]
guard=repo/'files/usr/libexec/xg2010g-dnsmasq-log-guard'
with tempfile.TemporaryDirectory(prefix='xg-dns-log-') as d:
    root=Path(d);(root/'uci').write_text('#!/bin/sh\nprintf "%s\\n" "$UCI_OUTPUT"\n');(root/'uci').chmod(0o755)
    env=dict(os.environ,PATH=d+':'+os.environ['PATH']); conf=root/'dnsmasq.conf'
    original=b'#log-facility=/old\n  log-facility=/dev/null\nserver=1.1.1.1\n'
    def run(value):
        env['UCI_OUTPUT']=value;subprocess.run(['sh',str(guard),str(conf)],check=True,env=env)
    conf.write_bytes(original);run('');assert conf.read_bytes()==original
    run("dhcp.cfg123.logfacility=''\n");assert conf.read_bytes()==original
    run("dhcp.cfg123.logfacility='/tmp/dnsmasq.log'\n")
    first=conf.read_bytes();assert first!=original and b'server=1.1.1.1' in first
    backup=root/'dnsmasq.conf.xg2010g-before-log-guard';assert backup.read_bytes()==original
    run("dhcp.cfg123.logfacility='/tmp/dnsmasq.log'\n");assert first==conf.read_bytes() and backup.read_bytes()==original
    run("dhcp.named.logfacility='/tmp/a'\ndhcp.other.logfacility='/tmp/b'");assert first==conf.read_bytes()
print('PASS: no-UCI, empty-UCI, duplicate, whitespace, backup and repeated log guard')

# Exercise image first-boot defaults separately from live package postinst.
import json
with tempfile.TemporaryDirectory(prefix='clients-firstboot-') as d:
    root=Path(d);state=root/'state.json';called=root/'guard-called'
    uci=root/'uci'
    uci.write_text("""#!/usr/bin/env python3
import os,sys,json
from pathlib import Path
p=Path(os.environ['UCI_STATE']);state=json.loads(p.read_text());args=[x for x in sys.argv[1:] if x!='-q']
if args[0]=='get':
 if args[1] not in state:sys.exit(1)
 print(state[args[1]])
elif args[0]=='set':
 k,v=args[1].split('=',1);state[k]=v;p.write_text(json.dumps(state))
elif args[0]!='commit':sys.exit(42)
""");uci.chmod(0o755)
    guard_stub=root/'guard';guard_stub.write_text('#!/bin/sh\ntouch "'+str(called)+'"\n');guard_stub.chmod(0o755)
    source=(repo/'Packages/Extras/luci-app-clients/root/etc/uci-defaults/95-clients-query-log').read_text()
    hook=root/'firstboot';hook.write_text(source.replace('/usr/libexec/xg2010g-dnsmasq-log-guard',str(guard_stub)))
    env=dict(os.environ,PATH=d+':'+os.environ['PATH'],UCI_STATE=str(state))
    baseline={'clients.global.enabled':'1','clients.dns.enabled':'1','dhcp.@dnsmasq[0]':'dnsmasq'}
    for initial,apply in [(baseline,True),(baseline|{'clients.global.enabled':'0'},False),
        (baseline|{'clients.dns.enabled':'0'},False),({'clients.global.enabled':'1'},False),
        (baseline|{'dhcp.@dnsmasq[0].logqueries':'0','dhcp.@dnsmasq[0].logfacility':'/tmp/custom'},True)]:
        state.write_text(json.dumps(initial));called.unlink(missing_ok=True)
        subprocess.run(['sh',str(hook)],env=env,check=True)
        result=json.loads(state.read_text())
        assert called.exists()==apply
        if apply:
            assert result['dhcp.@dnsmasq[0].logqueries']==initial.get('dhcp.@dnsmasq[0].logqueries','1')
            assert result['dhcp.@dnsmasq[0].logfacility']==initial.get('dhcp.@dnsmasq[0].logfacility','/tmp/dnsmasq.log')
            subprocess.run(['sh',str(hook)],env=env,check=True)
            assert json.loads(state.read_text())==result
        else:assert result==initial
print('PASS: first-boot DNS defaults, disabled collectors, absent DNS service, explicit choices and repeat execution')
