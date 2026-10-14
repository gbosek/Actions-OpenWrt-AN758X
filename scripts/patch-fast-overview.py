#!/usr/bin/env python3
"""Install independent status cards without changing the native CPU sampling helper."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
root = parser.parse_args().source
repo = Path(__file__).resolve().parents[1]
module = root / 'feeds/luci/modules/luci-mod-status'
page = module / 'htdocs/luci-static/resources/view/status/index.js'
text = page.read_text()
for marker in ('handleToggleSection:', 'poll_status:', "L.resource('view/status/include')", 'handleSaveApply: null'):
    assert marker in text, f'Unsupported overview source: {marker}'
page.write_bytes((repo / 'UI/status-index.js').read_bytes())
makefile = module / 'Makefile'
text = makefile.read_text()
if 'LUCI_MINIFY_JS:=0' not in text:
    assert 'include ../../luci.mk' in text, 'Unsupported status package Makefile'
    text = text.replace('include ../../luci.mk', 'LUCI_MINIFY_JS:=0\ninclude ../../luci.mk', 1)
makefile.write_text(text)
print('Overview renders immediately and updates cards independently, with one in-flight request per card')
