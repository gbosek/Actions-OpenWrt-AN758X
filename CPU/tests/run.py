#!/usr/bin/env python3
"""Host tests of the delivered helper and policy; no hardware accesses."""
from pathlib import Path
import subprocess, tempfile, os
repo=Path(__file__).resolve().parents[2]
patch=(repo/'kernel-patches/airoha/999-xg2010g-bl31-compatible-overclock.patch').read_text()
header=patch.split('+++ b/drivers/pmdomain/mediatek/xg2010g-cpu-boost.h\n',1)[1]
header='\n'.join(line[1:] for line in header.splitlines() if line.startswith('+'))+'\n'
with tempfile.TemporaryDirectory(prefix='xg2010g-boost-test-') as d:
 root=Path(d);(root/'xg2010g-cpu-boost.h').write_text(header)
 subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-g','-I',d,str(repo/'CPU/tests/boost-test.c'),'-o',str(root/'boost-test')],check=True)
 subprocess.run([str(root/'boost-test')],check=True)
subprocess.run(['python3',str(repo/'CPU/tests/policy-test.py')],check=True)
subprocess.run(['python3',str(repo/'CPU/tests/npu-test.py')],check=True)
