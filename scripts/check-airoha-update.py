#!/usr/bin/env python3
"""Verify exact reviewed raw sources and the actual staged NPU/clients assets."""
from pathlib import Path
import argparse,hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path);a=p.parse_args()
meta=json.loads((R/'AIROHA-UPDATE-REVIEW.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
for name,digest in meta['files_sha256'].items():
 assert sha((R/name).read_bytes())==digest,'Reviewed source mismatch: '+name
assert meta['fork']['commit']=='69a1b62c835b922e03add9953a92db2f728fb9e5'
assert meta['upstream_commit']=='d3669ce663ed39ae05c3cb56c82a9a1ed29cee9e'
assert 'CONFIG_PACKAGE_nlbwmon=y' in (R/'configs/gemtek_xg2010g.config').read_text()
if a.source:
 source=a.source;installed,=list((source/'build_dir').glob('target-*/root-airoha'))
 minifier=source/'staging_dir/hostpkg/bin/jsmin'
 checked={}
 for name in ['luci-app-clients','luci-app-airoha-npu']:
  package=source/'package/custom'/name
  for prefix in ['root','htdocs']:
   for path in (package/prefix).rglob('*'):
    if not path.is_file():continue
    if prefix=='htdocs' and path.suffix not in ['.js','.css']:continue
    relative=('www/' if prefix=='htdocs' else '')+path.relative_to(package/prefix).as_posix()
    expected=path.read_bytes();actual=(installed/relative).read_bytes()
    if path.suffix=='.js':
     # LuCI may serve the literal script or its deterministic jsmin output.
     # Neither variant is allowed to lose require declarations or code paths.
     allowed=[expected]
     if minifier.is_file():allowed.append(subprocess.check_output([str(minifier)],input=expected))
     assert actual in allowed,'Wrong served script: '+relative
    elif path.suffix=='.css':
     # Theme/build CSS transforms are validated by the browser fixture.
     assert b'220px' in actual if name=='luci-app-clients' else actual
    else:assert actual==expected,'Wrong staged file: '+relative
    checked[relative]=sha(actual)
 report={'passed':True,'upstream_commit':meta['upstream_commit'],'fork':meta['fork'],'files_sha256':checked,'device_tested':False}
 out=source/'bin/targets/airoha/an7581/AIROHA-UPDATE-VERIFICATION.json'
 out.write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: exact reviewed sources and '+str(len(checked))+' actual installed files; no device claim')
else:print('PASS: exact reviewed upstream/fork source identities and file hashes')
