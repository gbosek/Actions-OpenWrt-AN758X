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
