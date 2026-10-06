"""Check deterministic CPU and XG2010G PON temperature LuCI integration."""
from pathlib import Path
import ast
import json
import os
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
script = repo / 'scripts/integrate-xg2010g-ui.py'
ast.parse(script.read_text(encoding='utf-8'))

with tempfile.TemporaryDirectory(prefix='ui-integration-review-') as directory:
    root = Path(directory)
    backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
    page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
    acl_path = root / 'feeds/luci/modules/luci-mod-status/root/usr/share/rpcd/acl.d/luci-mod-status-index.json'
    backend.parent.mkdir(parents=True)
    page.parent.mkdir(parents=True)
    acl_path.parent.mkdir(parents=True)
    backend.write_text("\tgetCPUUsage: { call: function() { return { cpuusage: '?' }; } },\n\tgetTempInfo: {}\n", encoding='utf-8')
    page.write_text("""'use strict';
'require fs';
'require uci';
var callTempInfo = rpc.declare({
\tobject: 'luci',
\tmethod: 'getTempInfo'
});
return baseclass.extend({
\tload: function() {
\t\treturn Promise.all([
\t\t\tL.resolveDefault(callTempInfo(), {}),
\t\t\tuci.load('system')
\t\t]);
\t},
\trender: function(data) {
\t\tvar tempinfo = data[0],
\t\t\tunixtime    = data[7];
\t\tvar fields = [ _('CPU usage (%)'), cpuusage.cpuusage
\t\t];
\t\tif (tempinfo.tempinfo) {
\t\t\tfields.splice(6, 0, _('Temperature'));
\t\t\tfields.splice(7, 0, tempinfo.tempinfo);
\t\t}
\t\tvar table = E('table');
\t}
});
""", encoding='utf-8')
    acl_path.write_text(json.dumps({
        'luci-mod-status-index': {
            'description': 'Status page',
            'read': {'ubus': {'system': ['board']}, 'file': {'/etc/board.json': ['read']}}
        }
    }), encoding='utf-8')

    env = dict(os.environ, PROFILE='gemtek_xg2010g')
    subprocess.run([sys.executable, str(script), str(root)], check=True, env=env)
    first = (backend.read_bytes(), page.read_bytes(), acl_path.read_bytes())
    page_text = page.read_text(encoding='utf-8')
    backend_text = backend.read_text(encoding='utf-8')
    acl = json.loads(acl_path.read_text(encoding='utf-8'))['luci-mod-status-index']['read']
    assert "100.0 * (b.busy - a.busy)" in backend_text
    assert "cpuusage.cpuusage || _('Unavailable')" in page_text
    assert 'function readPonTemperature()' in page_text
    assert "fs.exec_direct('/usr/sbin/ponctl', args)" in page_text
    assert "uci.load('pon')" in page_text
    assert 'L.resolveDefault(readPonTemperature(), null)' in page_text
    assert 'ponTemperature = data[8]' in page_text
    assert "temperatureText + ' / ' + ponTemperatureText" in page_text
    assert page_text.count("uci.load('pon')") == 1
    assert 'exec' in acl['ubus']['file']
    assert 'pon' in acl['uci']
    assert acl['file']['/usr/sbin/ponctl --device * status --json'] == ['exec']
    assert acl['file']['/usr/sbin/ponctl status --json'] == ['exec']

    # Exercise the optional metric reader for valid, unavailable and implausible values.
    helper = page_text[page_text.index('function readPonTemperature()'):]
    helper = helper[:helper.index('\n}\n') + 2]
    node_test = r"""
const assert = require('node:assert/strict');
const helper = process.argv[1];
const makeReader = (output, device = 'pon0') => {
  const selected = device && /^[a-zA-Z0-9_.:-]+$/.test(device) ? device : null;
  return new Function('fs', 'L', 'uci', helper + '; return readPonTemperature;')(
  { exec_direct: async (path, args) => { assert.equal(path, '/usr/sbin/ponctl'); assert.deepEqual(args, selected ? ['--device', selected, 'status', '--json'] : ['status', '--json']); return output; } },
  { resolveDefault: (promise, fallback) => Promise.resolve(promise).catch(() => fallback) },
  { load: async () => null, sections: () => device ? [{ device }] : [] }
  );
};
(async () => {
  assert.equal(await makeReader(JSON.stringify({ frontend: { temperature_celsius: 53.27 } }))(), 53.27);
  assert.equal(await makeReader(JSON.stringify({ frontend: {} }))(), null);
  assert.equal(await makeReader(JSON.stringify({ frontend: { temperature_celsius: 'bad' } }))(), null);
  assert.equal(await makeReader(JSON.stringify({ frontend: { temperature_celsius: 200 } }))(), null);
  assert.equal(await makeReader(null)(), null);
  assert.equal(await makeReader(JSON.stringify({ frontend: { temperature_celsius: 48.5 } }), '../bad')(), 48.5);
})().catch(e => { console.error(e); process.exit(1); });
"""
    subprocess.run(['node', '-e', node_test, helper], check=True)
    subprocess.run(['node', '-e', 'new Function(process.argv[1]);', page_text], check=True)

    subprocess.run([sys.executable, str(script), str(root)], check=True, env=env)
    assert first == (backend.read_bytes(), page.read_bytes(), acl_path.read_bytes()), 'integration is not idempotent'

with tempfile.TemporaryDirectory(prefix='ui-integration-other-profile-') as directory:
    root = Path(directory)
    backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
    page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
    backend.parent.mkdir(parents=True)
    page.parent.mkdir(parents=True)
    backend.write_text("\tgetCPUUsage: {}\n\tgetTempInfo: {}\n", encoding='utf-8')
    page.write_text("var callTempInfo = rpc.declare({\n\tobject: 'luci',\n\tmethod: 'getTempInfo'\n});\n", encoding='utf-8')
    subprocess.run([sys.executable, str(script), str(root)], check=True, env=dict(os.environ, PROFILE='other_board'))
    assert 'readPonTemperature' not in page.read_text(encoding='utf-8')

print('PASS: CPU precision, optional PON temperature and exec ACL are deterministic and safe')
