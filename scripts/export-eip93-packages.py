#!/usr/bin/env python3
"""Export crypto-only offline APKs; never bundle a replacement kernel/libc."""
import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path


def export(source, output):
    roots = list((source / 'build_dir').glob('target-*/root-airoha'))
    assert len(roots) == 1
    records = {}
    for paragraph in (roots[0] / 'lib/apk/db/installed').read_text().split('\n\n'):
        fields = dict(line.split(':', 1) for line in paragraph.splitlines() if ':' in line)
        if 'P' in fields: records[fields['P']] = fields
    expected_kernel = records['kernel']['V']
    wanted = {'kmod-crypto-hw-eip93', 'kmod-cryptodev', 'openssl-util', 'libopenssl-devcrypto', 'libopenssl-conf'}
    pending = list(wanted)
    while pending:
        name = pending.pop()
        assert name in records, 'Uninstalled requested dependency: ' + name
        for dep in records[name].get('D', '').split():
            depname = re.split(r'[<>=~]', dep)[0]
            if depname.startswith('kmod-crypto-') and depname not in wanted:
                wanted.add(depname)
                pending.append(depname)
    assert not wanted & {'kernel', 'libc', 'libopenssl3'}, 'Core upgrade is forbidden in offline crypto bundle'
    apk = source / 'staging_dir/host/bin/apk'
    assert apk.is_file()
    candidates = {}
    for file in (source / 'bin').rglob('*.apk'):
        candidates.setdefault(file.name, set()).add(file.resolve())
    entries = []
    with tempfile.TemporaryDirectory(prefix='eip93-export-') as tmp:
        staging = Path(tmp)
        for name in sorted(wanted):
            version = records[name]['V']
            filename = name + '-' + version + '.apk'
            matches = sorted(candidates.get(filename, []))
            assert matches, 'Compiled APK not found: ' + filename
            hashes = {hashlib.sha256(file.read_bytes()).hexdigest() for file in matches}
            assert len(hashes) == 1, 'Ambiguous APK content: ' + filename
            file = matches[0]
            text = subprocess.check_output([str(apk), 'adbdump', str(file)], text=True)
            assert re.search(r'^\s+name: ' + re.escape(name) + r'$', text, re.M)
            assert re.search(r'^\s+version: ' + re.escape(version) + r'$', text, re.M)
            if name.startswith('kmod-'):
                deps = re.findall(r'^\s+- kernel=(\S+)\s*$', text, re.M)
                assert deps == [expected_kernel], 'APK kernel dependency differs from image: ' + filename
            (staging / filename).write_bytes(file.read_bytes())
            entries.append({'name': name, 'version': version, 'file': filename, 'sha256': next(iter(hashes))})
        manifest = {'kernel_dependency': expected_kernel, 'packages': entries,
                    'excluded_core_packages': ['kernel', 'libc', 'libopenssl3'],
                    'installation_rule': 'Compare running kernel ABI and simulate the offline APK transaction first; never force kernel dependencies or replace kernel metadata.'}
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        with tarfile.open(output, 'w:gz') as archive:
            for file in sorted(staging.iterdir()): archive.add(file, arcname=file.name)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = export(args.source.resolve(), args.output.resolve())
    print(json.dumps({'kernel_dependency': result['kernel_dependency'], 'package_count': len(result['packages'])}))
