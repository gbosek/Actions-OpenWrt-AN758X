#!/usr/bin/env python3
"""Exercise the actual post-build manifest gate before expensive compilation."""
import ast
import json
import re
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
checker = repo / 'scripts/check-xg2010g-build.py'
tree = ast.parse(checker.read_text())
# Run the real manifest loop, without argparse or the later staged-rootfs checks.
loop, = [node for node in tree.body if isinstance(node, ast.For)
         and isinstance(node.target, ast.Name) and node.target.id == 'manifest']
expected_node, = [node for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'expected' for t in node.targets)]
expected = ast.literal_eval(expected_node.value)
code = compile(ast.Module(body=[loop], type_ignores=[]), str(checker), 'exec')
mwan = json.loads((repo / 'MWAN4-SOURCE.json').read_text())
required = [
    'ttyd', 'luci-app-ttyd', 'luci-app-rtp2httpd', 'luci-app-clients',
    'mwan4', 'luci-app-mwan4', 'luci-i18n-mwan4-zh-cn',
    'luci-app-airoha-npu', 'luci-i18n-airoha-npu-zh-cn',
    'xg2010g-rps', 'luci-app-pon-status', 'luci-app-wol',
    'luci-i18n-wol-zh-cn', 'etherwake', 'flock',
    'luci-theme-argon', 'luci-app-argon-config', 'luci-i18n-argon-config-zh-cn',
    'cpufreq', 'luci-app-cpufreq', 'luci-i18n-cpufreq-zh-cn',
]
cases = 0
with tempfile.TemporaryDirectory(prefix='firmware-manifest-') as directory:
    manifest = Path(directory) / 'fixture.manifest'

    def check(packages, pattern, accept):
        global cases
        manifest.write_text(''.join(f'{name} - {version}\n' for name, version in packages.items()))
        try:
            exec(code, {'re': re, 'manifests': [manifest], 'version_pattern': pattern})
        except (AssertionError, KeyError):
            if accept:
                raise
        else:
            assert accept, 'Manifest gate accepted an obsolete/missing package'
        cases += 1

    for variant, (_, _, pattern) in expected.items():
        packages = dict.fromkeys(required, '1.0-r1')
        packages.update({
            'luci-theme-argon': '3.1.0-r20261022', 'luci-app-argon-config': '3.1.0-r20261022',
            'luci-i18n-argon-config-zh-cn': '3.1.0-r20261022', 'luci-app-clients': '0.1.0-r4',
            'kernel': '6.18.55~fixture-r1', 'rtp2httpd': '3.16.0-r1',
            'xg2010g-rps': '20261013-r3', 'luci-app-pon-status': '20261026-r14',
            'mwan4': mwan['backend']['version'],
            'luci-app-mwan4': mwan['frontend']['version'],
            'luci-app-airoha-npu': '2.0.0-r911' if variant == 'naoki' else '1.2.1-r105',
        })
        check(packages, pattern, True)
        check({name: version.replace('-r', '-') for name, version in packages.items()}, pattern, True)
        for name, version in [
            ('mwan4', '0.1.1-r9'), ('mwan4', '0.1.1-r11'),
            ('luci-app-mwan4', '1.0.0-r11'), ('kernel', '6.18.54-r1'),
            ('luci-app-airoha-npu', '2.0.0-r907'), ('mwan3', '1.0-r1'),
            ('kmod-mac80211', '1.0-r1'),
            ('luci-theme-argon', '2.4.7-r20260824'), ('luci-app-argon-config', '26.288'),
            ('luci-i18n-argon-config-zh-cn', 'unknown'), ('luci-app-clients', '0.1.0-r2'),
            ('luci-app-clients', '0.1.0-r3'),
            ('luci-app-airoha-npu', '2.0.0-r908' if variant == 'naoki' else '1.2.1-r102'),
        ]:
            check(packages | {name: version}, pattern, False)
        for name in ('mwan4', 'rtp2httpd', 'luci-app-ttyd', 'luci-app-pon-status'):
            check({k: v for k, v in packages.items() if k != name}, pattern, False)
print(f'PASS: {cases} actual manifest-gate cases; current declared MWAN4 versions accepted; obsolete, unknown and missing packages rejected. No staged-image or hardware claim.')
