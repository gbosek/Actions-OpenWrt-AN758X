#!/usr/bin/env python3
"""Compile shipped templates and check whole-value matching with real ucode."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('--report', type=Path)
args = parser.parse_args()
installed, = (args.source / 'build_dir').glob('target-*/root-airoha')
ucode = os.environ['UCODE_BIN']
with tempfile.TemporaryDirectory(prefix='argon31-runtime-') as directory:
    out = Path(directory)
    cmd = [ucode, '-L', str(installed / 'usr/share/ucode/*.uc'), '-e', '''
import { normalize_hex } from 'luci.argon-palette';
assert(normalize_hex('#AbC') == '#aabbcc');
assert(normalize_hex('#ABCDEF') == '#abcdef');
for (let bad in ['', 'red', '#1234', '#abcdef;}', '#abc\n.foo{}', '#abc\r', null, 123, ['#abc'], {}])
    assert(normalize_hex(bad) == null, 'partial CSS match accepted');
print('passed');
''']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout == 'passed', result.stderr
    templates = list((installed / 'usr/share/ucode/luci/template/themes/argon').glob('*.ut'))
    assert len(templates) == 11, 'Incomplete Argon templates'
    for template in templates:
        result = subprocess.run([ucode, '-T,', '-s',
            '-cno-interp,dynlink=fs,dynlink=uci,dynlink=luci.core,dynlink=luci.argon-branding,dynlink=luci.argon-palette',
            '-o', str(out / template.name), str(template)], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
report = {'status': 'passed', 'actual_ucode_color_cases': 12,
          'templates_compiled': len(templates), 'hardware_tested': False}
if args.report:
    args.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
