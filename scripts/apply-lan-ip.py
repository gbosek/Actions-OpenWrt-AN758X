#!/usr/bin/env python3
"""Set only the LAN fallback used when config_generate creates a fresh config."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
path = args.source / 'package/base-files/files/bin/config_generate'
text = path.read_text()
old = 'lan) ipad=${ipaddr:-"192.168.1.1"} ;;'
new = 'lan) ipad=${ipaddr:-"192.168.10.1"} ;;'
assert (text.count(old), text.count(new)) in [(1, 0), (0, 1)], 'Unrecognized default LAN generator'
path.write_text(text.replace(old, new, 1))
print('Fresh LAN defaults to 192.168.10.1; retained configs and board-specific addresses are preserved')
