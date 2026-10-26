#!/usr/bin/env python3
"""Install pinned screenshot-requested plugins without duplicate providers."""
import json, shutil, sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1];root=Path(sys.argv[1]).resolve()
meta=json.loads((repo/'Packages/Extras/SOURCE.json').read_text())
for name in meta['source_repositories']:
    source=repo/'Packages/Extras'/name;dest=root/'package/custom'/name
    for feed in (root/'feeds').glob('*'):
        assert not list(feed.rglob(name+'/Makefile')), 'Duplicate provider: '+name
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(source,dest)
    for path in (dest/'root').rglob('*'):
        if path.is_file() and path.read_bytes().startswith(b'#!'):path.chmod(0o755)
dest=root/'files/etc/xg2010g-requested-plugins.json';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(meta,indent=2)+'\n')
print('Installed pinned clients/Pushbot; feed plugin dependencies checked by package index')
