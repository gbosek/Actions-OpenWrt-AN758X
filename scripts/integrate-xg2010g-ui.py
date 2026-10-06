#!/usr/bin/env python3
"""Apply deterministic LuCI fixes after feeds have been installed."""
from pathlib import Path
import json
import os
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
profile = os.environ.get('PROFILE', '')

backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
text = backend.read_text()
start = text.index('\tgetCPUUsage: {')
end = text.index('\n\tget', start + 1)
text = text[:start] + '''\tgetCPUUsage: {
\t\tcall: function() {
\t\t\tconst sample = function() {
\t\t\t\tconst fh = open('/proc/stat', 'r');
\t\t\t\tif (!fh) return null;
\t\t\t\tconst line = fh.read('line');
\t\t\t\tfh.close();
\t\t\t\tconst m = match(line, /^cpu\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)(\\s+(\\d+))?/);
\t\t\t\tif (!m) return null;
\t\t\t\t// Guest time is already included in user/nice; do not count it twice.
\t\t\t\tconst busy = +m[1] + +m[2] + +m[3] + +m[6] + +m[7] + +(m[9] || 0);
\t\t\t\treturn { total: busy + +m[4] + +m[5], busy: busy };
\t\t\t};
\t\t\tconst a = sample();
\t\t\tsleep(500);
\t\t\tconst b = sample();
\t\t\tif (!a || !b || b.total <= a.total || b.busy < a.busy)
\t\t\t\treturn { cpuusage: '?' };
\t\t\tconst value = max(0, min(100, 100.0 * (b.busy - a.busy) / (b.total - a.total)));
\t\t\treturn { cpuusage: sprintf('%.1f%%', value) };
\t\t}
\t},
''' + text[end:]
backend.write_text(text)

page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
text = page.read_text()
# Optical power/current/voltage stay in the separate 15_pon card. Remove any
# older duplicate PON rows, then add only its temperature beside CPU temperature.
if '\t\tvar pon = {};' in text:
    begin = text.index('\t\tvar pon = {};')
    finish = text.index('\t\tvar table =', begin)
    text = text[:begin] + text[finish:]
text = text.replace('cpuusage.cpuusage\n', "cpuusage.cpuusage || _('Unavailable')\n")

if profile == 'gemtek_xg2010g':
    if 'function readPonTemperature()' not in text:
        marker = "var callTempInfo = rpc.declare({\n\tobject: 'luci',\n\tmethod: 'getTempInfo'\n});"
        if marker not in text:
            raise SystemExit('Cannot find getTempInfo declaration in status overview')
        helper = '''

function readPonTemperature() {
\treturn L.resolveDefault(uci.load('pon'), null).then(function() {
\t\tvar sections = [];
\t\ttry { sections = uci.sections('pon', 'xpon') || []; } catch (e) {}
\t\tvar section = sections.find(function(s) {
\t\t\treturn typeof s.device == 'string' && /^[a-zA-Z0-9_.:-]+$/.test(s.device);
\t\t});
\t\tvar args = section ? [ '--device', section.device, 'status', '--json' ] : [ 'status', '--json' ];

\t\treturn L.resolveDefault(fs.exec_direct('/usr/sbin/ponctl', args), null).then(function(output) {
\t\t\tif (!output)
\t\t\t\treturn null;

\t\t\ttry {
\t\t\t\tvar snapshot = JSON.parse(output);
\t\t\t\tvar raw = snapshot && snapshot.frontend ? snapshot.frontend.temperature_celsius : null;
\t\t\t\tif (raw === null || raw === undefined || raw === '')
\t\t\t\t\treturn null;

\t\t\t\tvar value = Number(raw);
\t\t\t\treturn isFinite(value) && value >= -40 && value <= 125 ? value : null;
\t\t\t} catch (e) {
\t\t\t\treturn null;
\t\t\t}
\t\t});
\t});
}
'''
        text = text.replace(marker, marker + helper, 1)

    if 'L.resolveDefault(readPonTemperature(), null)' not in text:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().rstrip(',') == "uci.load('system')":
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = indent + "uci.load('system'),"
                lines.insert(i + 1, indent + 'L.resolveDefault(readPonTemperature(), null)')
                text = '\n'.join(lines) + ('\n' if text.endswith('\n') else '')
                break
        else:
            raise SystemExit('Cannot find system UCI load in status overview')

    if 'ponTemperature = data[8]' not in text:
        marker = 'unixtime    = data[7];'
        if marker not in text:
            raise SystemExit('Cannot find status overview renderer data slots')
        text = text.replace(marker, 'unixtime    = data[7],\n\t\t\tponTemperature = data[8];', 1)

    if 'var ponTemperatureText =' not in text:
        marker = '\t\tif (tempinfo.tempinfo) {'
        if marker not in text:
            raise SystemExit('Cannot find temperature row in status overview')
        temperature = '''\t\tvar ponTemperatureText = (typeof ponTemperature == 'number' && isFinite(ponTemperature))
\t\t\t? _('PON') + ': ' + ponTemperature.toFixed(1) + '°C' : null;
\t\tvar temperatureText = tempinfo.tempinfo || null;
\t\tif (ponTemperatureText)
\t\t\ttemperatureText = temperatureText ? temperatureText + ' / ' + ponTemperatureText : ponTemperatureText;

\t\tif (temperatureText) {'''
        text = text.replace(marker, temperature, 1)
        text = text.replace('fields.splice(7, 0, tempinfo.tempinfo);', 'fields.splice(7, 0, temperatureText);', 1)

page.write_text(text)

if profile == 'gemtek_xg2010g':
    acl_path = root / 'feeds/luci/modules/luci-mod-status/root/usr/share/rpcd/acl.d/luci-mod-status-index.json'
    acl = json.loads(acl_path.read_text())
    status_acl = acl.setdefault('luci-mod-status-index', {}).setdefault('read', {})
    uci_acl = status_acl.setdefault('uci', [])
    if 'pon' not in uci_acl:
        uci_acl.append('pon')
    ubus_acl = status_acl.setdefault('ubus', {})
    file_methods = ubus_acl.setdefault('file', [])
    if 'exec' not in file_methods:
        file_methods.append('exec')
    file_acl = status_acl.setdefault('file', {})
    file_acl['/usr/sbin/ponctl --device * status --json'] = ['exec']
    file_acl['/usr/sbin/ponctl status --json'] = ['exec']
    acl_path.write_text(json.dumps(acl, indent='\t', ensure_ascii=False) + '\n')

print('Applied precise CPU sampling and XG2010G PON temperature overview fixes')
