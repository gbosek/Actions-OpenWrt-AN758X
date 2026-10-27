#!/usr/bin/env python3
"""Replace the two reviewed Argon feed providers with one integrated release."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'Packages/Themes'
META = json.loads((SOURCE / 'SOURCE.json').read_text())
FLAGS = '\n# Retain auditable release assets; no target-side behavior change.\nLUCI_MINIFY_JS:=0\nLUCI_MINIFY_CSS:=0\n'


def files(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def install(root):
    root = root.resolve()
    pins = json.loads((root / 'files/etc/firmware-feed-pins.json').read_text())
    assert pins['selected']['luci']['commit'] == META['feed_commit'], 'Unreviewed LuCI feed'
    expected = META['files_sha256']
    assert {k: v for k, v in files(SOURCE).items() if k != 'SOURCE.json'} == expected, 'Argon release payload changed'
    destinations = {}
    # Validate everything before replacing either provider. Feed install symlinks
    # stay valid because these are replacements at their original feed paths.
    for name, provider in META['providers'].items():
        dest = root / 'feeds/luci' / provider['path']
        assert dest.is_dir() and not dest.is_symlink(), 'Missing/aliased provider: ' + name
        assert dest.resolve().is_relative_to(root), 'Provider outside build root'
        for tree in ('feeds', 'package'):
            for makefile in (root / tree).rglob(name + '/Makefile'):
                assert makefile.resolve() == (dest / 'Makefile').resolve(), 'Duplicate provider: ' + str(makefile)
        source_files = {k.removeprefix(name + '/'): v for k, v in expected.items() if k.startswith(name + '/')}
        current = files(dest)
        installed_files = dict(source_files)
        if name == 'luci-theme-argon':
            installed_files['Makefile'] = hashlib.sha256((SOURCE / name / 'Makefile').read_text().replace('include $(TOPDIR)/feeds/luci/luci.mk', FLAGS + '\ninclude $(TOPDIR)/feeds/luci/luci.mk').encode()).hexdigest()
        if current != installed_files:
            assert current.get('Makefile') == provider['old_makefile_sha256'], 'Unknown/modified provider: ' + name
        destinations[name] = dest
    for name, dest in destinations.items():
        shutil.rmtree(dest)
        shutil.copytree(SOURCE / name, dest)
        if name == 'luci-theme-argon':
            makefile = dest / 'Makefile'
            makefile.write_text(makefile.read_text().replace('include $(TOPDIR)/feeds/luci/luci.mk', FLAGS + '\ninclude $(TOPDIR)/feeds/luci/luci.mk'))
        for path in (dest / 'root').rglob('*'):
            if path.is_file() and path.read_bytes().startswith(b'#!'):
                path.chmod(0o755)
    overlay = root / 'files/etc/config/argon'
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text((SOURCE / 'luci-theme-argon/root/etc/config/argon').read_text().replace("online_wallpaper 'none'", "online_wallpaper 'bing'"))
    (root / 'files/etc/xg2010g-argon-source.json').write_text(json.dumps(META, indent=2) + '\n')
    print('Installed Argon 3.1.0 and empty compatibility package; old UI ownership removed')


if __name__ == '__main__':
    install(Path(sys.argv[1]))
