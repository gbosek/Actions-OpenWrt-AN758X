"""Check the actual UI patch against an extracted local-image fixture."""
from pathlib import Path
import ast
import shutil
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
fixture = repo.parent / 'output/GitHub24-review/local-image'
script = repo / 'scripts/integrate-xg2010g-ui.py'
ast.parse(script.read_text(encoding='utf-8'))
with tempfile.TemporaryDirectory(dir=repo.parent / 'output/GitHub24-review') as directory:
    root = Path(directory)
    backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
    page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
    backend.parent.mkdir(parents=True)
    page.parent.mkdir(parents=True)
    shutil.copyfile(fixture / 'usr/share/rpcd/ucode/luci', backend)
    # Match upstream's formatted Promise block; compiled firmware is minified.
    page.write_text("load: function() {\n\t\treturn Promise.all([\n\t\t\tuci.load('system'),\n\t\t\tL.resolveDefault(uci.load('pon'), null)\n\t\t]).then(function(data) {\n\t\t\treturn data;\n\t\t});\n\t},\n\n\trender: function(data) {\n\t\tvar pon = {};\n\t\tfields.push(pon);\n\t\tvar table = E('table');\n\t}\n", encoding='utf-8')
    subprocess.run([sys.executable, str(script), str(root)], check=True)
    first = (backend.read_bytes(), page.read_bytes())
    assert "100.0 * (b.busy - a.busy)" in backend.read_text()
    assert "uci.load('system')" in page.read_text()
    assert "uci.load('pon')" not in page.read_text()
    assert '.then(function(data)' not in page.read_text()
    subprocess.run([sys.executable, str(script), str(root)], check=True)
    assert first == (backend.read_bytes(), page.read_bytes()), 'patch is not idempotent'
print('PASS: integration syntax, float CPU calculation, redundant PON removal and repeat application')
