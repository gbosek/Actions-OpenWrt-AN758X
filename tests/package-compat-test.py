#!/usr/bin/env python3
"""Check package restoration, unchanged disabled default and collision rejection."""
from pathlib import Path
import hashlib, json, subprocess, sys, tempfile
repo = Path(__file__).resolve().parents[1]
metadata = json.loads((repo/'BASELINE-PACKAGE-COMPAT.json').read_text())
script = repo/'scripts/apply-package-compat.py'
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    destination = root/'package/custom/rtp2httpd'
    for _ in range(2):
        subprocess.run([sys.executable,str(script),str(root)],check=True)
    for name, digest in metadata['files_sha256'].items():
        assert hashlib.sha256((destination/name).read_bytes()).hexdigest() == digest
    assert "option 'enabled' '0'" in (destination/'files/rtp2httpd.config').read_text()
    assert 'PKG_VERSION:=3.16.0' in (destination/'Makefile').read_text()
    assert json.loads((root/'files/etc/firmware-package-compat.json').read_text()) == metadata
    (destination/'Makefile').write_text('conflicting package\n')
    failure=subprocess.run([sys.executable,str(script),str(root)],capture_output=True,text=True)
    assert failure.returncode and 'Conflicting local package' in failure.stderr
    assert (destination/'Makefile').read_text() == 'conflicting package\n'
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    provider = root/'feeds/packages/net/rtp2httpd'
    provider.mkdir(parents=True)
    failure=subprocess.run([sys.executable,str(script),str(root)],capture_output=True,text=True)
    assert failure.returncode and 'Unexpected second rtp2httpd provider' in failure.stderr
    assert not (root/'package/custom/rtp2httpd').exists()
print('PASS: exact retained backend, idempotence, disabled default and both provider collision guards')
