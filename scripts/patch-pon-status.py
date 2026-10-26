#!/usr/bin/env python3
"""Install a dedicated full-width PON view under a fresh LuCI module name."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
root = parser.parse_args().source
repo = Path(__file__).resolve().parents[1]
package = root / 'package/custom/luci-app-pon-status'
# Replace only this package; the PON driver and ONU feed remain pinned.
assert package.resolve() != (repo / 'Packages/PON/luci-app-pon-status').resolve()
if package.exists():
    shutil.rmtree(package)
shutil.copytree(repo / 'Packages/PON/luci-app-pon-status', package)

directory = package / 'htdocs/luci-static/resources/view/status/include'
assert directory.is_dir(), 'PON status package has not been installed'
module = '29a_xg2010g_pon.js'
data = (repo / 'UI/15_pon.js').read_bytes()
# Keep just one PON include. The new module name also avoids reusing the old
# include instance when LuCI has already cached it in an open browser session.
for name in ('15_pon.js', '15_xg2010g_pon.js', '29a_pon.js', module):
    (directory / name).unlink(missing_ok=True)
(directory / module).write_bytes(data)
makefile = package / 'Makefile'
text = makefile.read_text()
text, count = re.subn(r'^PKG_RELEASE:=.*$', 'PKG_RELEASE:=14', text, flags=re.M)
assert count == 1, 'Unsupported PON status package release definition'
text = re.sub(r'^LUCI_MINIFY_JS:=.*\n', '', text, flags=re.M)
text, count = re.subn(r'^(include .*luci\.mk)$', r'LUCI_MINIFY_JS:=0\n\1', text, flags=re.M)
assert count == 1, 'Unsupported PON status LuCI Makefile'
makefile.write_text(text)
metadata = root / 'files/etc/pon-status-layout.json'
metadata.parent.mkdir(parents=True, exist_ok=True)
metadata.write_text(json.dumps({
    'layout': 'horizontal-naoki-v1', 'package_release': 14,
    'module': 'view.status.include.29a_xg2010g_pon',
    'display_name': 'PON', 'device_name': 'pon0',
    'sha256': hashlib.sha256(data).hexdigest(),
    'source': json.loads((repo / 'UI/PON-SOURCE.json').read_text()),
}, ensure_ascii=False, indent=2) + '\n')
print('PON horizontal-naoki-v1: full-width card with compact transparent rate rows')
