#!/usr/bin/env python3
"""Apply reviewed DNS/route/sticky fixes to the pinned MWAN4 backend."""
import re, subprocess, sys
from pathlib import Path

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
repo=Path(__file__).resolve().parents[1]
backend=root/'package/custom/mwan4'
if not backend.is_dir():
    raise SystemExit('Pinned MWAN4 backend is missing')
patch=repo/'Runtime/mwan4-routing.patch'
base=['patch','--batch','--forward','--fuzz=0','-p1','-d',str(backend),'-i',str(patch)]
if subprocess.run(base+['--dry-run'],capture_output=True).returncode==0:
    subprocess.run(base,check=True)
elif subprocess.run(base+['-R','--dry-run'],capture_output=True).returncode!=0:
    raise SystemExit('MWAN4 routing patch does not match the pinned backend')
make=backend/'Makefile'
release=11 if (repo/'Config/AIROHA.txt').exists() else 10
text,n=re.subn(r'^PKG_RELEASE:=.*$','PKG_RELEASE:='+str(release),make.read_text(),flags=re.M)
assert n==1
make.write_text(text)
print(f'MWAN4 r{release}: provider DNS priority, missing PPP default recovery, safe sticky marks, repeatable route snapshots')
