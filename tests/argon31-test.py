#!/usr/bin/env python3
"""Prove provider replacement is idempotent and refuses ambiguous sources."""
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('argon31', repo / 'scripts/apply-argon31.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='argon31-') as directory:
    root = Path(directory)
    for name, provider in m.META['providers'].items():
        dest = root / 'feeds/luci' / provider['path']
        dest.mkdir(parents=True)
        (dest / 'Makefile').write_bytes((repo / 'tests/fixtures' / (name + '.baseline.Makefile')).read_bytes())
        legacy = dest / 'root/legacy-owned-file'
        legacy.parent.mkdir(parents=True)
        legacy.write_text('legacy UI ownership must be removed')
        link = root / 'package/feeds/luci' / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(dest, target_is_directory=True)
    pins = root / 'files/etc/firmware-feed-pins.json'
    pins.parent.mkdir(parents=True)
    pins.write_text(json.dumps({'selected': {'luci': {'commit': m.META['feed_commit']}}}))
    for _ in range(2):
        m.install(root)
    assert "online_wallpaper 'bing'" in (root / 'files/etc/config/argon').read_text()
    theme = root / 'feeds/luci/themes/luci-theme-argon'
    compat = root / 'feeds/luci/applications/luci-app-argon-config'
    assert not (compat / 'root').exists() and not (compat / 'htdocs').exists(), 'Legacy UI must release ownership'
    assert (theme / 'root/usr/share/argon/config-integrated').is_file()
    assert 'PKG_PO_VERSION:=$(PKG_VERSION)-r$(PKG_RELEASE)' in (theme / 'Makefile').read_text()
    assert 'LUCI_BASENAME:=argon-config' in (theme / 'Makefile').read_text()
    assert not any(p.suffix == '.ut' and p.read_bytes().startswith(b'\x1buc') for p in theme.rglob('*.ut'))
    for failure in ('duplicate', 'modified', 'pin'):
        if failure == 'duplicate':
            changed = root / 'package/custom/luci-theme-argon/Makefile'
            changed.parent.mkdir(parents=True)
            changed.write_text('duplicate')
        elif failure == 'modified':
            changed = theme / 'htdocs/luci-static/resources/view/argon-config.js'
            saved = changed.read_bytes()
            changed.write_text('changed provider')
        else:
            changed = pins
            saved = changed.read_bytes()
            changed.write_text(json.dumps({'selected': {'luci': {'commit': 'unreviewed'}}}))
        try:
            m.install(root)
        except AssertionError:
            pass
        else:
            raise AssertionError('Installer accepted ' + failure)
        if failure == 'duplicate':
            shutil.rmtree(changed.parent)
        else:
            changed.write_bytes(saved)
    m.install(root)
print('PASS: fixed Argon release, single UI/file owner, repeat install, Chinese version, duplicate/modified/unreviewed rejection')
