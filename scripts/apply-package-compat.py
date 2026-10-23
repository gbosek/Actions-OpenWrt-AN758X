#!/usr/bin/env python3
"""Restore a hash-pinned existing package missing from the compatibility feed."""
from pathlib import Path
import argparse, hashlib, json, shutil

def install(root):
    repo = Path(__file__).resolve().parents[1]
    metadata = json.loads((repo/'BASELINE-PACKAGE-COMPAT.json').read_text())
    source = repo/'Packages/compat/rtp2httpd'
    destination = root/'package/custom/rtp2httpd'
    # The selected old feed deliberately lacks this backend. A second provider
    # must be reviewed instead of silently creating duplicate package recipes.
    for candidate in (root/'feeds/packages/net/rtp2httpd', root/'package/feeds/packages/rtp2httpd'):
        assert not candidate.exists(), 'Unexpected second rtp2httpd provider: '+str(candidate)
    for name, digest in metadata['files_sha256'].items():
        data = (source/name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, 'Compatibility payload changed: '+name
        target = destination/name
        assert not target.exists() or target.read_bytes() == data, 'Conflicting local package: '+str(target)
    for name in metadata['files_sha256']:
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
    (destination/'files/rtp2httpd.init').chmod(0o755)
    record = root/'files/etc/firmware-package-compat.json'
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(metadata, indent=2)+'\n')
    print('Restored existing rtp2httpd 3.16.0-r1 backend; default configuration unchanged')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    install(parser.parse_args().source.resolve())
