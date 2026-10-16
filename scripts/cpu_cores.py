#!/usr/bin/env python3
"""Use the repository CPU usage helper and its scalar LuCI RPC field."""
import argparse
import hashlib
import re
from pathlib import Path

RPC = "\tgetCPUUsage: {\n        call: function() {\n            let reason = 'cpu_sampler_unavailable';\n            const fd = popen('/usr/libexec/xg2010g-cpuusage');\n            if (fd) {\n                const text = fd.read('all');\n                const status = fd.close();\n                if (!text) reason = 'cpu_sampler_empty_output';\n                else try {\n                    const value = json(text);\n                    if (type(value) == 'object' && type(value.cpuusage) == 'string' &&\n                        value.cpuusage != '?' && (value.last_success_at != null || value.error != null))\n                        return value;\n                    reason = 'cpu_sampler_invalid_response';\n                } catch (e) { reason = 'cpu_sampler_invalid_json'; }\n            } else reason = 'cpu_sampler_popen_failed';\n            try {\n                const cached = json(readfile('/tmp/xg2010g-cpuusage.last.json') || 'null');\n                if (type(cached) == 'object' && type(cached.cpuusage) == 'string') {\n                    cached.stale = true;\n                    cached.error = reason;\n                    return cached;\n                }\n            } catch (e) {}\n            return { cpuusage: 'Unavailable', stale: true, error: reason,\n                     sampled_at: null, last_success_at: null, sample_ms: null };\n        }\n    },\n"
DISPLAY = "function cpuSampleDisplay(sample) {\n    sample = sample || {};\n    var value = String(sample.cpuusage || 'Unavailable').replace(/SYS\\s*\\(system\\s*\\+\\s*IRQ\\s*\\+\\s*softirq\\)/gi, 'SYS');\n    var children = [ value ];\n    if ((sample.stale || sample.error) && sample.last_success_at)\n        children.push(E('span', { 'class': 'cpu-sample-warning', style: 'color:#b45309' }, '（旧数据）'));\n    return E('span', { 'class': 'cpu-sample-values' }, children);\n}\n\n"


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
    end = text.index('\tgetTempInfo: {', start)
    backend.write_text(text[:start] + RPC + text[end:])
    text = page.read_text()
    text = re.sub(r'// BEGIN XG2010G FOUR-CORE CPU\n.*?// END XG2010G FOUR-CORE CPU\n', '', text, flags=re.S)
    text = text.replace('renderCPUCoreUsage(cpuusage)', "cpuusage.cpuusage || _('Unavailable')")
    text, count = re.subn(r'^function cpuSampleDisplay\(sample\) \{\n.*?^\}\n*', '', text, flags=re.M|re.S)
    assert count <= 1, 'Duplicate CPU sample display helper'
    if 'function cpuSampleDisplay(' not in text:
        assert 'return baseclass.extend({' in text
        text = text.replace('return baseclass.extend({', DISPLAY + 'return baseclass.extend({', 1)
    # Both upstream overview variants have the same row, with different spacing.
    text, n = re.subn(r"(_\('CPU usage \(%\)'\),\s*)(?:cpuusage\.cpuusage(?:\s*\|\|\s*_\('Unavailable'\))?|cpuSampleDisplay\(cpuusage\))", r'\1cpuSampleDisplay(cpuusage)', text)
    if n != 1:
        raise ValueError('Cannot uniquely identify the CPU usage row')
    text, n = re.subn(r'L\.resolveDefault\(callCPUUsage\(\),\s*\{\}\)', "callCPUUsage().catch(function(error) { return { cpuusage: 'Unavailable', stale: true, error: 'RPC: ' + String(error) }; })", text)
    assert n == 1 or "error: 'RPC: '" in text, 'CPU RPC error handling absent'
    page.write_text(text)
    refresh_luci_cache_version(root)
    print('CPU overview: structured sample, SYS includes IRQ/softirq, explicit errors and last-success time')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, nargs='?', default=Path.cwd())
    args = parser.parse_args()
    apply_cpu_core_view(args.source.resolve())
