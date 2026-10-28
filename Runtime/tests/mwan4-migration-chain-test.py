#!/usr/bin/env python3
"""Run the actual paired 60->90 scripts with isolated config/UCI persistence."""
from pathlib import Path
import argparse,json,os,subprocess,tempfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);root=p.parse_args().source.resolve()
front=(root/'package/custom/luci-app-mwan4/root/etc/uci-defaults/60_luci-mwan4').read_text()
back=(root/'package/custom/mwan4/files/etc/uci-defaults/90-mwan4').read_text()
fake=r'''import json,shlex,sys
from pathlib import Path
path=Path(sys.argv[1]);action=sys.argv[2];args=sys.argv[3:]
state=json.loads(path.read_text()) if path.exists() else {}
def parse(text):
 result={};sid=None
 for line in text.splitlines():
  a=shlex.split(line,comments=True)
  if not a:continue
  if a[0]=='config':sid=a[2];result[sid]={'.type':a[1]}
  elif a[0]=='option':result[sid][a[1]]=a[2]
  elif a[0]=='list':result[sid].setdefault(a[1],[]).append(a[2])
 return result
if action=='load':state=parse(Path(args[0]).read_text())
elif action=='get':
 value=state.get(args[0],{}).get(args[1],args[2] if len(args)>2 else '')
 print(' '.join(value) if isinstance(value,list) else value)
elif action=='sections':print(' '.join(k for k,v in state.items() if v['.type']==args[0]))
elif action=='set':
 sid=args[0];state.setdefault(sid,{})
 if len(args)==2:state[sid]['.type']=args[1]
 else:state[sid][args[1]]=args[2]
elif action=='rename':
 sid,old,new=args
 if old in state[sid]:state[sid][new]=state[sid].pop(old)
elif action=='remove':state[args[0]].pop(args[1],None)
elif action=='add_list':
 sid,key,value=args;old=state[sid].get(key,[])
 state[sid][key]=(old if isinstance(old,list) else [old])+[value]
elif action=='export':
 lines=[]
 for sid,section in state.items():
  lines.append('config '+section['.type']+' '+shlex.quote(sid))
  for key,value in section.items():
   if key=='.type':continue
   for item in value if isinstance(value,list) else [value]:
    lines.append((' list ' if isinstance(value,list) else ' option ')+key+' '+shlex.quote(item))
 Path(args[0]).write_text('\n'.join(lines)+'\n')
else:raise Exception(action)
if action not in ['get','sections']:path.write_text(json.dumps(state))
'''
base="""config globals 'globals'
 option mmx_mask '0x3F00'
config member 'r1'
 option interface 'wan'
config member 'r2'
 option interface 'wanb'
config policy 'balanced'
 list use_member 'r1'
 list use_member 'r2'
config rule 'all_traffic'
 option use_policy 'balanced'
 option local '0'
config interface 'wan'
 option family 'ipv4'
 option enabled '1'
"""
modern=base.replace('config member','config route').replace('config policy','config strategy').replace('use_member','use_route').replace('use_policy','use_strategy')
partial=modern.replace("list use_route 'r2'","list use_member 'r2'\n list use_member 'r1'")
cases=[('legacy',base,False),('already_renamed',base.replace('config member','config route').replace('config policy','config strategy'),False),('mixed_lists',partial,False),('modern',modern,False),('mwan3_import',base,True),('empty',"config globals 'globals'\n option xg2010g_rule_semantics '1'\n",False)]
for name,config,import3 in cases:
 with tempfile.TemporaryDirectory(prefix='mwan4-migrate-chain-') as d:
  tmp=Path(d);confdir=tmp/'config';confdir.mkdir();conf=confdir/'mwan4';state=tmp/'uci.json'
  conf.write_text("config globals 'globals'\n" if import3 else config)
  if import3:(confdir/'mwan3').write_text(config)
  fakepath=tmp/'uci.py';fakepath.write_text(fake)
  functions=tmp/'functions.sh'
  functions.write_text('''call_uci() { python3 "$AUDIT_UCI" "$AUDIT_STATE" "$@"; }
config_load() { call_uci load "$AUDIT_CONFIG"; }
config_get() { local value; value=$(call_uci get "$2" "$3" "${4:-}"); eval "$1=\\\"$value\\\""; }
config_foreach() { local sid; for sid in $(call_uci sections "$2"); do "$1" "$sid"; done; }
uci_set() { shift; call_uci set "$@"; }
uci_rename() { shift; call_uci rename "$@"; }
uci_remove() { shift; call_uci remove "$@"; }
uci_add_list() { shift; call_uci add_list "$@"; }
uci_commit() { call_uci export "$AUDIT_CONFIG"; }
uci() { return 1; }
''')
  env=os.environ|{'AUDIT_UCI':str(fakepath),'AUDIT_STATE':str(state),'AUDIT_CONFIG':str(conf)}
  def run(script):
   safe=script.replace('/etc/config/',str(confdir)+'/').replace('/etc/init.d/',str(tmp/'no-init')+'/').replace('/lib/functions.sh',str(functions))
   subprocess.run(['sh','-c','logger() { :; };\n'+safe],env=env,check=True,capture_output=True,text=True)
  run(front)
  if not import3:assert conf.read_text()==config,'Frontend must not partially migrate types'
  run(back);first=json.loads(state.read_text())
  if name!='empty':
   assert first['balanced']['.type']=='strategy'
   assert first['balanced']['use_route']==['r1','r2'],(name,first)
   assert 'use_member' not in first['balanced']
   assert first['all_traffic']['use_strategy']=='balanced'
   assert first['all_traffic']['local']=='0','Explicit operator choice changed'
   assert first['r1']['.type']==first['r2']['.type']=='route'
   assert first['wan']['family']==['ipv4']
  else:assert list(first)==['globals']
  backup=confdir/'mwan4.pre-paired-migration'
  old_backup=backup.read_bytes() if backup.exists() else None
  if name in ['legacy','already_renamed','mixed_lists','mwan3_import']:assert old_backup==config.encode(),name
  run(front);run(back);second=json.loads(state.read_text())
  assert second==first,(name,'Second migration changed configuration')
  assert (backup.read_bytes() if backup.exists() else None)==old_backup,'Backup overwritten'
  if import3:assert (confdir/'mwan3.migrated').read_text()==config
  print('PASS migration chain:',name)
print('PASS: six complete first-boot/mixed/new/import/empty cases, backups, explicit settings and repeat migration')
