#!/usr/bin/env python3
"""Verify the built FIT, staged metadata and existing MDIO reset call order."""
from pathlib import Path
import argparse, gzip, hashlib, importlib.util, json

repo = Path(__file__).resolve().parents[1]
meta = json.loads((repo / 'Boot/PHY-PRE-ID-SOURCE.json').read_text())
spec = importlib.util.spec_from_file_location('fit', repo / 'scripts/check-compatible-boost.py')
fit = importlib.util.module_from_spec(spec); spec.loader.exec_module(fit)

def check_dtb(data):
    nodes, _ = fit.fdt(data)
    return check_nodes(nodes)

def check_nodes(nodes):
    assert b'gemtek,xg2010g\0' in nodes['/']['compatible'], 'Unexpected board'
    for address, gpio in meta['phys'].items():
        path = '/soc/switch@1fb58000/mdio/ethernet-phy@' + address
        props = nodes[path]
        assert props['reset-before-id-read'] == b'', 'Pre-ID reset missing in actual DTB: ' + path
        assert fit.cells(props['reg']) == (int(address),)
        assert fit.cells(props['reset-gpios'])[1:] == (gpio, 1), 'GPIO/polarity changed'
        for key, expected in [('reset-assert-us', meta['reset_assert_us']), ('reset-deassert-us', meta['reset_deassert_us'])]:
            assert fit.cells(props[key]) == (expected,), 'Reset timing changed'
    return {'phy_addresses': list(meta['phys']), 'pre_id_reset': True}

def check_kernel(image):
    raw = image.read_bytes(); nodes, total = fit.fdt(raw)
    kernels = []
    for path, props in nodes.items():
        if not path.startswith('/images/') or path.count('/') != 2 or props.get('type') != b'kernel\0': continue
        data = props.get('data')
        if data is None:
            start = fit.cells(props['data-position'])[0] if 'data-position' in props else ((total + 3) & ~3) + fit.cells(props['data-offset'])[0]
            size = fit.cells(props['data-size'])[0]
            assert 0 <= start <= start + size <= len(raw)
            data = raw[start:start + size]
        compression = props.get('compression', b'none\0')
        assert compression in (b'gzip\0', b'none\0')
        data = gzip.decompress(data) if compression == b'gzip\0' else data
        assert b'reset-before-id-read\0' in data and b'PHY pre-ID reset\0' in data, 'Actual Image lacks pre-ID reset support'
        kernels.append(hashlib.sha256(data).hexdigest())
    assert kernels, 'Missing actual kernel Image'
    return kernels

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('root', type=Path); p.add_argument('--report', type=Path); a = p.parse_args()
    root = a.root.resolve()
    kernels = list((root / 'build_dir').glob('target-*/linux-airoha_an7581/linux-6.18.55'))
    assert len(kernels) == 1, 'Ambiguous prepared kernel'
    source = kernels[0] / 'drivers/net/mdio/fwnode_mdio.c'; code = source.read_text()
    call = code.index('rc = fwnode_mdiobus_reset_phy_before_id_read(child);')
    assert call < code.index('phy = get_phy_device(bus, addr, is_c45);')
    assert 'if (rc == 0)\n\t\tphy->mdio.reset_state = 0;' in code, 'Duplicate registration reset is not suppressed'
    obj = source.with_suffix('.o'); assert obj.is_file(), 'MDIO support was not compiled'
    object_data = obj.read_bytes()
    assert object_data[:5] == b'\x7fELF\x02' and int.from_bytes(object_data[18:20], 'little') == 183, 'MDIO object is not AArch64'
    staged = list((root / 'build_dir').glob('target-*/root-airoha/etc/xg2010g-phy-pre-id-reset.json'))
    assert staged and all(json.loads(p.read_text()) == meta for p in staged), 'Staged reset metadata mismatch'
    images = list((root / 'bin/targets/airoha/an7581').glob('*gemtek_xg2010g*-sysupgrade.itb')); assert images
    checked = {image.name: dict(check_nodes(fit.board_from_fit(image)), kernel_sha256=check_kernel(image)) for image in images}
    result = {'status': 'passed', 'images': checked, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest(), 'crc_root_cause_proven': False, 'hardware_tested': False}
    if a.report: a.report.parent.mkdir(parents=True, exist_ok=True); a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
