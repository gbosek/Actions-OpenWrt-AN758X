#!/usr/bin/env python3
"""Apply deterministic LuCI fixes after feeds have been installed."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
backend = root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci'
text = backend.read_text()
start = text.index('\tgetCPUUsage: {')
end = text.index('\n\tget', start + 1)
text = text[:start] + '''	getCPUUsage: {
		call: function() {
			const sample = function() {
				const fh = open('/proc/stat', 'r');
				if (!fh) return null;
				const line = fh.read('line');
				fh.close();
				const m = match(line, /^cpu\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)(\\s+(\\d+))?/);
				if (!m) return null;
				// Guest time is already included in user/nice; do not count it twice.
				const busy = +m[1] + +m[2] + +m[3] + +m[6] + +m[7] + +(m[9] || 0);
				return { total: busy + +m[4] + +m[5], busy: busy };
			};
			const a = sample();
			sleep(500);
			const b = sample();
			if (!a || !b || b.total <= a.total || b.busy < a.busy)
				return { cpuusage: '?' };
			const value = max(0, min(100, 100.0 * (b.busy - a.busy) / (b.total - a.total)));
			return { cpuusage: sprintf('%.1f%%', value) };
		}
	},
''' + text[end:]
backend.write_text(text)
page = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js'
text = page.read_text()
# Optical telemetry belongs to the separate 15_pon card. Remove duplicated rows.
if '\t\tvar pon = {};' in text:
    begin = text.index('\t\tvar pon = {};')
    finish = text.index('\t\tvar table =', begin)
    text = text[:begin] + text[finish:]
text = text.replace('cpuusage.cpuusage\n', "cpuusage.cpuusage || _('Unavailable')\n")
page.write_text(text)
print('Applied CPU sampling precision and separate PON overview card fixes')
