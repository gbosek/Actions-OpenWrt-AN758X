#!/usr/bin/env python3
"""Exercise the shipped migration with an isolated UCI shell fixture."""
import argparse, os, subprocess, tempfile
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
root=p.parse_args().source
text=(root/'package/custom/mwan4/files/etc/uci-defaults/90-mwan4').read_text()
# Never touch the host's /etc/config. Execute the actual remaining shell code.
text=text[text.index('. /lib/functions.sh'):].replace('. /lib/functions.sh', ':',1)
stubs='''
config_load() { :; }
config_get() {
 local value=''
 case "$2:$3" in
  globals:xg2010g_rule_semantics) value="$SCHEMA";;
  globals:mmx_mask) value=0x3f00;;
  local0:local) value=0;;
  local1:local) value=1;;
 esac
 eval "$1=\\\"$value\\\""
}
config_foreach() {
 case "$2" in
  globals) "$1" globals;;
  rule) "$1" legacy; "$1" local0; "$1" local1;;
 esac
}
uci_set() { printf '%s\\n' "$*" >> "$TEST_LOG"; }
uci() { return 1; }
uci_commit() { printf 'commit %s\\n' "$*" >> "$TEST_LOG"; }
'''
with tempfile.TemporaryDirectory() as directory:
    log=Path(directory)/'calls'
    for schema,expected in [('',True),('1',False)]:
        log.write_text('')
        subprocess.run(['sh','-c',stubs+text],check=True,
                       env=os.environ|{'SCHEMA':schema,'TEST_LOG':str(log)})
        calls=log.read_text().splitlines()
        assert ('mwan4 legacy local 1' in calls)==expected,calls
        assert not any('local0 local' in x or 'local1 local' in x for x in calls),calls
        assert calls[-2:]==['mwan4 globals xg2010g_rule_semantics 1','commit mwan4'],calls
    assert "option xg2010g_rule_semantics '1'" in (root/'package/custom/mwan4/files/etc/config/mwan4').read_text()
print('PASS: legacy local routing retained once; explicit settings and fresh/new rule semantics preserved')
