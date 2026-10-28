#!/usr/bin/env python3
"""Run pinned upstream/adaptation backend tests with the build's host ucode."""
import argparse,json,os,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
root=p.parse_args().source.resolve()
ucode=Path(os.environ['UCODE']).resolve()
assert ucode.is_file(),'Host ucode is required; never skip the backend suite'
with tempfile.TemporaryDirectory(prefix='xg-mwan-pair-') as d:
    work=Path(d)
    package=work/'backend'
    shutil.copytree(root/'package/custom/mwan4',package,ignore=shutil.ignore_patterns('.git'))
    bindir=work/'bin';bindir.mkdir()
    wrapper=bindir/'ucode'
    wrapper.write_text('#!/bin/sh\nexec "'+str(ucode)+'" -L "'+str(ucode.parent.parent/'lib/ucode')+'" "$@"\n')
    wrapper.chmod(0o755)
    env=os.environ|{'PATH':str(bindir)+':'+os.environ['PATH']}
    result=subprocess.run(['bash','tests/run_tests.sh'],cwd=package,env=env,capture_output=True,text=True)
    print(result.stdout)
    if result.stderr:print(result.stderr)
    assert '58 tests, 58 okay, 0 failures' in result.stdout,'Incomplete or failed paired backend suite'
    assert result.returncode==0,'Paired backend tests failed'
print('PASS: all 58 pinned backend suites including read-only RPC and disabled/down links')
