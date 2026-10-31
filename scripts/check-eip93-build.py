#!/usr/bin/env python3
"""Check selected crypto packages and actual staged AArch64 driver/engine files."""
import argparse
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def elf(path):
    raw = path.read_bytes()
    assert raw[:4] == b'\x7fELF' and raw[18:20] == b'\xb7\0', 'Not AArch64 ELF: ' + str(path)
    return raw


def check(source, config_only=False):
    meta = json.loads((REPO / 'EIP93-SOURCE.json').read_text())
    config = (source / '.config').read_text()
    for name in meta['packages']:
        assert re.search(r'^CONFIG_PACKAGE_' + re.escape(name) + '=y$', config, re.M), 'Crypto package not selected: ' + name
    assert re.search(r'^CONFIG_OPENSSL_ENGINE=y$', config, re.M)
    assert not re.search(r'^CONFIG_OPENSSL_ENGINE_BUILTIN=y$', config, re.M), 'Expected dynamic devcrypto engine'
    if config_only:
        return {'selected': meta['packages'], 'scope': 'Configuration only; no compiled or device evidence'}
    kernels = list((source / 'build_dir').glob('target-*/linux-*/linux-6.18.60'))
    assert len(kernels) == 1
    kernel = kernels[0]
    kernel_config = (kernel / '.config').read_text()
    assert re.search(r'^CONFIG_CRYPTO_DEV_EIP93=m$', kernel_config, re.M)
    assert re.search(r'^CONFIG_CRYPTO_HW=y$', kernel_config, re.M)
    abi = (kernel / '.vermagic').read_text().strip()
    assert re.fullmatch(r'[0-9a-f]{32}', abi), 'Missing OpenWrt kernel ABI hash'
    roots = list((source / 'build_dir').glob('target-*/root-airoha'))
    assert len(roots) == 1
    root = roots[0]
    for name, expected in meta['prepared_driver_sha256'].items():
        assert hashlib.sha256((kernel / name).read_bytes()).hexdigest() == expected, 'Unreviewed crypto driver: ' + name
    manifests = list((source / 'bin/targets/airoha/an7581').glob('*.manifest'))
    assert manifests, 'Missing firmware package manifest'
    for manifest in manifests:
        packages = dict(re.findall(r'^(\S+) - (.+)$', manifest.read_text(), re.M))
        assert set(meta['packages']) <= packages.keys(), 'Crypto stack missing from image manifest'
    assert json.loads((root / 'etc/eip93-build-source.json').read_text()) == meta
    files = ['lib/modules/6.18.60/crypto-hw-eip93.ko', 'lib/modules/6.18.60/cryptodev.ko',
             'usr/bin/openssl', 'usr/lib/engines-3/devcrypto.so', 'etc/ssl/modules.cnf.d/devcrypto.cnf']
    for name in files[:4]:
        raw = elf(root / name)
        if name.endswith('.ko'):
            assert b'vermagic=6.18.60 ' in raw, 'Wrong kernel module version: ' + name
    for mod in ('crypto-hw-eip93', 'cryptodev'):
        assert any(mod in f.read_text() for f in (root / 'etc/modules.d').glob('*')), 'Crypto module autoload missing: ' + mod
    engine_config = (root / files[-1]).read_text()
    assert re.search(r'^DIGESTS\s*=\s*NONE\s*$', engine_config, re.M), 'Unsafe default digest engine activation'
    assert (root / files[-1]).read_bytes() == (source / 'package/libs/openssl/files/devcrypto.cnf').read_bytes()
    database = (root / 'lib/apk/db/installed').read_text()
    records = {}
    for paragraph in database.split('\n\n'):
        fields = dict(line.split(':', 1) for line in paragraph.splitlines() if ':' in line)
        if 'P' in fields: records[fields['P']] = fields
    kernel_version = records['kernel']['V']
    assert kernel_version == '6.18.60~' + abi + '-r1', 'Kernel package ABI differs from configured kernel'
    for name in ('kmod-crypto-hw-eip93', 'kmod-cryptodev'):
        assert 'kernel=' + kernel_version in records[name]['D'].split(), 'Staged crypto/kernel ABI mismatch: ' + name
    files.append('etc/eip93-build-source.json')
    return {'kernel_package': kernel_version, 'kernel_abi': abi, 'files': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files},
            'package_versions': {name: records[name]['V'] for name in meta['packages']},
            'dynamic_engine': True, 'digests_disabled': True, 'kernel_dependencies_match': True,
            'scope': 'Actual staged files/ELF/package ABI; no device binding or encryption test', 'hardware_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--config-only', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = check(args.source, args.config_only)
    if args.report: args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
