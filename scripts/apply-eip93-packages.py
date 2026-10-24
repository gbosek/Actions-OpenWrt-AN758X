#!/usr/bin/env python3
"""Record and validate the stock EIP93/cryptodev/OpenSSL source selection."""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
root = parser.parse_args().source.resolve()
meta = json.loads((REPO / 'EIP93-SOURCE.json').read_text())
for name, expected in meta['package_source_sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, 'Unreviewed EIP93 package input: ' + name
dest = root / 'files/etc/eip93-build-source.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(meta, indent=2) + '\n')
print('Pinned stock Airoha EIP93, cryptodev and dynamic OpenSSL devcrypto selection')
