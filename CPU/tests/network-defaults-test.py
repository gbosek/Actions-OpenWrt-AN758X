#!/usr/bin/env python3
"""Fresh images and explicit starts must not inject routing policies."""
from pathlib import Path
import os,re,subprocess,tempfile
repo=Path(__file__).resolve().parents[2]
config=repo/'files/etc/config/mwan4'
sections=re.findall(r"^config\s+(\S+)\s+['\"]?(\w+)",config.read_text(),re.M)
assert sections==[('globals','globals')],sections
assert re.findall(r"^\s*option\s+(\S+)",config.read_text(),re.M)==['mmx_mask','rule_mask','source_routing','xg2010g_rule_semantics']
with tempfile.TemporaryDirectory(prefix='mwan4-no-preset-') as directory:
 root=Path(directory);binpath=root/'bin';binpath.mkdir();log=root/'calls'
 for name in ['uci','ubus','ip','nft','logger']:
  path=binpath/name;path.write_text('#!/bin/sh\necho "$0 $*" >> "$TEST_LOG"\nexit 1\n');path.chmod(0o755)
 env=os.environ|{'PATH':str(binpath)+':'+os.environ['PATH'],'TEST_LOG':str(log)}
 board=root/'board';board.write_text('gemtek,xg2010g\n')
 reference=root/'stock';reference.write_text('stock package template\n')
 saved=root/'mwan4';hook=root/'hook'
 text=(repo/'files/usr/libexec/xg2010g-mwan4-preset').read_text()
 for old,new in [('/tmp/sysinfo/board_name',board),('/usr/share/xg2010g/mwan4-stock.config',reference),('/etc/config/mwan4',saved)]:
  text=text.replace(old,str(new))
 hook.write_text(text)
 for text in [config.read_text(),'stock package template\n',"config rule 'custom'\n option dest_ip '192.0.2.7'\n"]:
  saved.write_text(text);before=saved.read_bytes()
  subprocess.run(['sh',str(hook)],env=env,check=True)
  assert saved.read_bytes()==before and not log.exists()
print('PASS: fresh globals only; explicit start makes no UCI/network/routing calls; saved policies unchanged')
