#!/usr/bin/env python3
"""Show all four XG2010G CPU cores while retaining the scalar LuCI RPC field."""
import argparse
import hashlib
import re
from pathlib import Path

RPC = r'''	getCPUUsage: {
		call: function() {
			const sample = function() {
				const fh = open('/proc/stat', 'r');
				if (!fh) return null;
				const cpus = {};
				let line;
				while ((line = fh.read('line')) != null) {
					const m = match(line, /^(cpu[0-3])\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(\s+(\d+))?/);
					if (!m) continue;
					// Guest counters are already included in user/nice.
					const busy = +m[2] + +m[3] + +m[4] + +m[7] + +m[8] + +(m[10] || 0);
					cpus[m[1]] = { total: busy + +m[5] + +m[6], busy: busy };
				}
				fh.close();
				return cpus;
			};
			const a = sample();
			sleep(500);
			const b = sample();
			const cores = [];
			let totalTicks = 0, busyTicks = 0;
			for (let i = 0; i < 4; i++) {
				const name = 'cpu' + i;
				let usage = null;
				if (a && b && a[name] && b[name] && b[name].total > a[name].total && b[name].busy >= a[name].busy) {
					const total = b[name].total - a[name].total;
					const busy = b[name].busy - a[name].busy;
					usage = max(0, min(100, 100.0 * busy / total));
					totalTicks += total;
					busyTicks += busy;
				}
				push(cores, usage);
			}
			return {
				cpuusage: totalTicks > 0 ? sprintf('%.1f%%', 100.0 * busyTicks / totalTicks) : '?',
				cpucores: cores
			};
		}
	},'''

JS = '''// BEGIN XG2010G FOUR-CORE CPU
function renderCPUCoreUsage(result) {
	var cores = result && Array.isArray(result.cpucores) ? result.cpucores : [];
	return E('div', {
		'class': 'cpu-core-usage',
		'style': 'display:flex;flex-wrap:wrap;gap:0.4em 1.5em'
	}, [0, 1, 2, 3].map(function(i) {
		var value = cores[i];
		var usage = typeof value == 'number' && isFinite(value)
			? Math.max(0, Math.min(100, value)).toFixed(1) + '%' : _('Unavailable');
		return E('span', { 'style': 'white-space:nowrap' }, [
			E('strong', {}, 'CPU' + i + ': '), usage
		]);
	}));
}
// END XG2010G FOUR-CORE CPU
'''


def paths(root):
    return (
        root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci',
        root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js',
    )


def refresh_luci_cache_version(root):
    backend, page = paths(root)
    digest = hashlib.sha256(backend.read_bytes() + page.read_bytes())
    app = root / 'package/custom/luci-app-airoha-npu/htdocs'
    for path in sorted(app.glob('**/*.js')):
        digest.update(path.relative_to(app).as_posix().encode())
        digest.update(path.read_bytes())
    makefile = root / 'feeds/luci/modules/luci-base/src/Makefile'
    text, count = re.subn(
        r'\$\(LUCI_VERSION\)(?:-xg2010g-ui-[0-9a-f]{12})?',
        '$(LUCI_VERSION)-xg2010g-ui-' + digest.hexdigest()[:12], makefile.read_text())
    if count != 1:
        raise ValueError('Cannot uniquely identify LuCI cache version generation')
    makefile.write_text(text)


def apply_cpu_core_view(root):
    backend, page = paths(root)
    text = backend.read_text()
    start = text.index('\tgetCPUUsage: {')
    end = text.index('\n\tget', start + 1)
    backend.write_text(text[:start] + RPC + text[end:])
    text = page.read_text()
    pattern = r'// BEGIN XG2010G FOUR-CORE CPU\n.*?// END XG2010G FOUR-CORE CPU\n'
    if re.search(pattern, text, re.S):
        text = re.sub(pattern, lambda _: JS, text, flags=re.S)
    else:
        marker = 'return baseclass.extend({'
        if text.count(marker) != 1:
            raise ValueError('Cannot identify the LuCI system overview renderer')
        text = text.replace(marker, JS + '\n' + marker, 1)
    text, count = re.subn(
        r"\bcpuusage\.cpuusage(?:\s*\|\|\s*_\('Unavailable'\))?",
        'renderCPUCoreUsage(cpuusage)', text)
    if count == 0 and 'renderCPUCoreUsage(cpuusage)' not in text:
        raise ValueError('Cannot identify the CPU usage row')
    if count > 1:
        raise ValueError('More than one CPU usage field was found')
    page.write_text(text)
    refresh_luci_cache_version(root)
    print('CPU overview configured to display CPU0, CPU1, CPU2 and CPU3 separately')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, nargs='?', default=Path.cwd())
    args = parser.parse_args()
    apply_cpu_core_view(args.source.resolve())
