#!/usr/bin/env python3
"""Check the source-prepare boundary where OpenWrt has not made .config yet."""
import sys
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / 'scripts'))
from check_ppe_functions import find_kernel

checks = 0


def rejected(build_dir, count):
    global checks
    try:
        find_kernel(build_dir)
    except ValueError as error:
        assert f'found {count}' in str(error), error
    else:
        raise AssertionError('Missing or ambiguous prepared sources were accepted')
    checks += 1


with tempfile.TemporaryDirectory(prefix='ppe-prepare-test-') as directory:
    build = Path(directory)
    rejected(build, 0)
    kernel = build / 'target-aarch64_cortex-a53_musl/linux-airoha_an7581/linux-6.18.52'
    driver = kernel / 'drivers/net/ethernet/airoha'
    driver.mkdir(parents=True)
    (driver / 'airoha_ppe.c').write_text('/* directory-discovery fixture */\n')
    rejected(build, 0)
    (driver / 'airoha_eth.h').write_text('/* directory-discovery fixture */\n')
    assert not (kernel / '.config').exists()
    assert find_kernel(build) == kernel
    checks += 1
    (kernel / '.config').write_text('CONFIG_NET_AIROHA=y\n')
    assert find_kernel(build) == kernel
    checks += 1
    wrong = build / 'target-other/linux-airoha_an7581/linux-6.17.1/drivers/net/ethernet/airoha'
    wrong.mkdir(parents=True)
    for name in ('airoha_ppe.c', 'airoha_eth.h'):
        (wrong / name).write_text('/* wrong-version fixture */\n')
    assert find_kernel(build) == kernel
    checks += 1
    other = build / 'target-other/linux-airoha_an7581/linux-6.18.54/drivers/net/ethernet/airoha'
    other.mkdir(parents=True)
    for name in ('airoha_ppe.c', 'airoha_eth.h'):
        (other / name).write_text('/* ambiguous-source fixture */\n')
    rejected(build, 2)

assert checks == 6
print('PASS: 6 PPE prepare/configured discovery checks; no .config requirement, missing/ambiguous sources rejected')
