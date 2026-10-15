#!/usr/bin/env python3
"""Exercise the actual PON installer, including upgrades and repeat installs."""
import hashlib
import json
import runpy
import subprocess
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='xg2010g-pon-install-') as directory:
    root = Path(directory)
    package = root / 'package/custom/luci-app-pon-status'
    includes = package / 'htdocs/luci-static/resources/view/status/include'
    includes.mkdir(parents=True)
    (package / 'Makefile').write_text('PKG_VERSION:=0.4.6\nPKG_RELEASE:=6\nLUCI_MINIFY_JS:=0\ninclude $(TOPDIR)/feeds/luci/luci.mk\n')
    (includes / '15_pon.js').write_text('old browser module')
    for _ in range(2):
        subprocess.run(['python3', str(repo / 'scripts/patch-pon-status.py'), str(root)], check=True)
        assert not (includes / '15_pon.js').exists()
        assert sorted(p.name for p in includes.iterdir()) == ['15_xg2010g_pon.js']
        data = (includes / '15_xg2010g_pon.js').read_bytes()
        assert data == (repo / 'UI/15_pon.js').read_bytes()
        makefile = (package / 'Makefile').read_text()
        assert makefile.count('LUCI_MINIFY_JS:=0') == 1
        assert makefile.count('PKG_RELEASE:=8') == 1
        meta = json.loads((root / 'files/etc/pon-status-layout.json').read_text())
        assert meta['sha256'] == hashlib.sha256(data).hexdigest()
        assert meta['layout'] == 'fullwidth-v3'
    # Verify the real cache-version generator sees the newly named module.
    luci = root / 'feeds/luci/modules'
    backend = luci / 'luci-base/root/usr/share/rpcd/ucode/luci'
    page = luci / 'luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
    version = luci / 'luci-base/src/Makefile'
    for p, content in [(backend, 'rpc fixture'), (page, 'system fixture'), (version, 'LUCI_VERSION=$(LUCI_VERSION)\n')]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    refresh = runpy.run_path(str(repo / 'scripts/cpu_cores.py'))['refresh_luci_cache_version']
    refresh(root)
    old_version = version.read_text()
    (includes / '15_xg2010g_pon.js').write_bytes(data + b'\n// changed layout\n')
    refresh(root)
    assert old_version != version.read_text(), 'Browser cache version ignored the new PON module'
print('PASS: PON installer removes the legacy module, installs one fresh module, preserves bytes and records revision/hash idempotently')
