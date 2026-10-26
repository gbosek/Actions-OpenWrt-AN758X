#!/usr/bin/env python3
import os,subprocess,tempfile
from pathlib import Path
repo=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='xg-rpc-guard-') as d:
    root=Path(d);backend=root/'backend';backend.touch();backend.chmod(0o755)
    def exe(name,text):
        p=root/name;p.write_text('#!/bin/sh\n'+text);p.chmod(0o755);return p
    reload=exe('reload','echo reload >> "$EVENTS"; touch "$READY"\n')
    exe('ubus','echo list >> "$EVENTS"\n[ "$MODE" = present ] || { [ "$MODE" = after ] && [ -e "$READY" ]; } || exit 0\necho luci.airoha_npu\n')
    exe('sleep','exit 0\n');exe('logger','exit 0\n')
    source=(repo/'Runtime/root/etc/init.d/xg2010g-npu-rpc-guard').read_text().replace('/usr/libexec/rpcd/luci.airoha_npu',str(backend)).replace('/etc/init.d/rpcd',str(reload))
    env=dict(os.environ,PATH=d+':'+os.environ['PATH'],EVENTS=str(root/'events'),READY=str(root/'ready'))
    for mode,expected,lists,reloads in [('present',0,1,0),('after',0,2,1),('never',1,11,1)]:
        (root/'events').unlink(missing_ok=True);(root/'ready').unlink(missing_ok=True);env['MODE']=mode
        proc=subprocess.run(['sh','-c',source+'\nstart\n'],env=env)
        assert proc.returncode==expected,(mode,proc.returncode)
        events=(root/'events').read_text().splitlines();assert events.count('list')==lists and events.count('reload')==reloads,(mode,events)
print('PASS: registered, reload success, bounded failure; no second CPU policy owner')
