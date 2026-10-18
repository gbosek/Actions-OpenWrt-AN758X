#!/usr/bin/env python3
"""Run actual patched ucode functions against duplicate-route and sticky fixtures."""
import argparse, json, os, re, subprocess, tempfile
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args()
backend=a.source/'package/custom/mwan4/files/lib/mwan4'
ucode=os.environ['UCODE']

def function(text,name):
    start=text.index('function '+name+'(');brace=text.index('{',start);depth=1;end=brace+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'test.uc'
    body=function((backend/'mwan4rtmon.uc').read_text(),'add_all_routes')
    fixture='''let commands=[], warnings=[];
let family='ipv4', ip='ip -4';
let system=function(s) {push(commands,s);return 0;};
let iface_active=function(iface,fam) {return true;};
let m={update_dev_to_table:function(){},
 uci_foreach:function(type,fn){fn({'.name':'wan'});fn({'.name':'wanb'});},
 get_iface_id:function(n){return n=='wan'?1:2;},get_families:function(n){return ['ipv4'];},
 get_routes:function(f){return ['default dev pppoe-wan','192.168.10.0/24 dev br-lan','default dev other','fe80::/64 dev other'];},
 route_line_dev:function(line,f){return line=='default dev pppoe-wan'?1:null;},
 cmd_lines:function(s){push(commands,s);return index(s,'route add')>=0?['File exists']:[];},
 LOG:function(...args){push(warnings,args);}};
'''
    path.write_text(fixture+body+'\nadd_all_routes();add_all_routes();print(sprintf("%J",{commands,warnings}));')
    result=json.loads(subprocess.check_output([ucode,str(path)],text=True))
    assert not result['warnings'],result
    commands=result['commands'];assert len(commands)==6 and commands[:3]==commands[3:]
    assert all('route replace table' in s for s in commands)
    assert not any('dev other' in s for s in commands)
    body=function((backend/'mwan4.uc').read_text(),'set_user_rules')
    fixture='''let NFT_TABLE='mwan4', NFT_PREFIX='mwan4';
let mwan4={mmx_mask:'0x3f00',mmx_default:'0x3f00',mmx_blackhole:'0x3d00',mmx_unreachable:'0x3e00',no_ipv6:0};
let uci_foreach=function(type,fn){fn({'.name':'https'});};
let _build_user_rule=function(s,fam){return {rule:'https',is_strategy_jump:true,sticky:true,timeout:600,use_strategy:'balanced',match_str:'tcp dport 443'};};
let _collect_sticky_ifaces=function(...args){return ['wan','wanb'];};
let nft_file=function(...args){print(join('\\n',slice(args,2)));};
'''
    path.write_text(fixture+body+'\nset_user_rules();')
    nft=subprocess.check_output([ucode,str(path)],text=True)
    lines=[s for s in nft.splitlines() if 'update @mwan4_rule_' in s]
    assert len(lines)==2 and any('ip6 saddr' in s for s in lines)
    for line in lines:
        tests=re.findall(r'meta mark & (0x[0-9a-f]+) != (0x[0-9a-f]+|0)',line)
        assert len(tests)==4,line
        for mark,expected in [(0,False),(0x100,True),(0x200,True),(0x3d00,False),(0x3e00,False),(0x3f00,False),(0x10001,False),(0x10101,True)]:
            assert all((mark & int(mask,0))!=int(value,0) for mask,value in tests)==expected,(line,mark)
print('PASS: repeated route snapshots, foreign defaults excluded, real IPv4/IPv6 sticky rules reject zero/default/blackhole/unreachable marks')
