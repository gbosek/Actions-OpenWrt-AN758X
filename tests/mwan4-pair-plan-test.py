#!/usr/bin/env python3
"""Reject a mixed pair or unwanted built-in routing presets."""
from pathlib import Path
import json,re
repo=Path(__file__).resolve().parents[1]
meta=json.loads((repo/'MWAN4-SOURCE.json').read_text())
clone=(repo/'diy-part1.sh').read_text()
for kind,name,version in [('backend','mwan4','0.1.1-r29'),('frontend','luci-app-mwan4','1.0.0-r16')]:
    entry=meta[kind]
    assert entry['version']==version
    assert 'clone_at https://github.com/gbosek/'+name+' '+entry['fork_commit']+' ' in clone
    assert entry['upstream']=='brauliobo/'+name
    assert len(entry['installed_files_sha256'])>10
assert meta['translation']['template_entries']==1337 and meta['translation']['untranslated']==0
cfg=(repo/'files/etc/config/mwan4').read_text()
assert re.findall(r'^config\s+(\w+)',cfg,re.M)==['globals']
assert 'wanb' not in cfg and 'speed_' not in cfg and '192.168.' not in cfg
for script in ['apply-runtime-fixes.py','apply-mwan4-routing-fixes.py','apply-mwan4-default-off.py']:
    assert 'PKG_RELEASE:=' not in (repo/'scripts'/script).read_text(),'Old release mutation remains'
assert 'Runtime/mwan4-routing.patch' not in (repo/'scripts/apply-mwan4-routing-fixes.py').read_text()
assert 'verify_installed(installed,repo)' in (repo/'scripts/check-xg2010g-build.py').read_text()
print('PASS: immutable complete pair, Chinese catalog, no presets and no legacy double-patch/downgrade')
