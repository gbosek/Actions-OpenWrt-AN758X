#!/usr/bin/env python3
"""Use the repository CPU usage helper and its scalar LuCI RPC field."""
import argparse
import hashlib
import re
from pathlib import Path

RPC = r'''	getCPUUsage: {
		call: function() {
			if (!access('/sbin/cpuusage'))
				return { cpuusage: '?' };
			const fd = popen('/sbin/cpuusage');
			if (!fd)
				return { cpuusage: '?' };
			const value = fd.read('all');
			fd.close();
			return { cpuusage: trim(value || '') || '?' };
		}
	},'''


def paths(root):
    return (
        root / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci',
        root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js',
    )


def refresh_luci_cache_version(root):
    backend, page = paths(root)
    digest = hashlib.sha256(backend.read_bytes() + page.read_bytes())
    overview = root / 'feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/index.js'
    if overview.exists():
        digest.update(overview.read_bytes())
    pon_dir = root / 'package/custom/luci-app-pon-status/htdocs/luci-static/resources/view/status/include'
    for pon in sorted(pon_dir.glob('*.js')):
        digest.update(pon.name.encode())
        digest.update(pon.read_bytes())
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
    # The native helper already formats all four core values in one string.
    pattern = r'// BEGIN XG2010G FOUR-CORE CPU\n.*?// END XG2010G FOUR-CORE CPU\n'
    text = re.sub(pattern, '', text, flags=re.S)
    text = text.replace('renderCPUCoreUsage(cpuusage)', "cpuusage.cpuusage || _('Unavailable')")
    if 'cpuusage.cpuusage' not in text:
        raise ValueError('Cannot identify the CPU usage row')
    page.write_text(text)
    refresh_luci_cache_version(root)
    print('CPU overview uses the unchanged repository /sbin/cpuusage helper (CPU0–CPU3)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, nargs='?', default=Path.cwd())
    args = parser.parse_args()
    apply_cpu_core_view(args.source.resolve())
