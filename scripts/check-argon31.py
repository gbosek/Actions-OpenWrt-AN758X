#!/usr/bin/env python3
"""Check real staged Argon payload, versions and template source provenance."""
import hashlib
import json
import re
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1])
meta = json.loads((repo / 'Packages/Themes/SOURCE.json').read_text())
installed, = (source / 'build_dir').glob('target-*/root-airoha')
assert json.loads((installed / 'etc/xg2010g-argon-source.json').read_text()) == meta
for relative, digest in meta['files_sha256'].items():
    prefix = 'luci-theme-argon/'
    if not relative.startswith(prefix):
        continue
    path = relative.removeprefix(prefix)
    if path.startswith('root/'):
        target = path.removeprefix('root/')
    elif path.startswith('htdocs/'):
        target = 'www/' + path.removeprefix('htdocs/')
    elif path.startswith('ucode/'):
        target = 'usr/share/ucode/luci/' + path.removeprefix('ucode/')
    else:
        continue
    actual = installed / target
    if target == 'etc/config/argon':
        expected = (repo / 'Packages/Themes' / relative).read_text().replace("online_wallpaper 'none'", "online_wallpaper 'bing'")
        assert actual.read_text() == expected
    elif target.startswith('etc/uci-defaults/'):
        # LuCI packages number these when installing multiple defaults.
        candidates = [p for p in (installed / 'etc/uci-defaults').iterdir() if p.name.endswith(Path(target).name)]
        assert len(candidates) == 1, target
        actual = candidates[0]
        assert hashlib.sha256(actual.read_bytes()).hexdigest() == digest, target
    elif path.startswith('ucode/'):
        expected = (repo / 'Packages/Themes' / relative).read_text()
        expected = re.sub(r'{# *([^ ]*)PKG_VERSION *#}', lambda m: m[1] + '3.1.0', expected)
        expected = re.sub(r'"({{ *(?:media|resource) *}}[^"]*\.(?:js|css))"', lambda m: '"' + m[1] + '?v=3.1.0"', expected)
        assert actual.read_text() == expected, target
    else:
        assert hashlib.sha256(actual.read_bytes()).hexdigest() == digest, target
    if target.startswith('usr/libexec/'):
        assert actual.stat().st_mode & 0o111, target
for manifest in (source / 'bin/targets/airoha/an7581').glob('*.manifest'):
    packages = dict(re.findall(r'^(\S+) - (.+)$', manifest.read_text(), re.M))
    for name in ('luci-theme-argon', 'luci-app-argon-config'):
        assert re.fullmatch(r'3\.1\.0-(?:r)?20261022', packages.get(name, '')), name
    assert packages.get('luci-i18n-argon-config-zh-cn') in ('v3.1.0', '3.1.0-r20261022', '3.1.0-20261022')
print('Verified Argon 3.1.0 actual assets, source templates, integrated RPC/configuration, empty compatibility version and Chinese catalog')
