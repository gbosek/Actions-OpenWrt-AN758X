#!/usr/bin/env python3
"""Check board-only enablement, idempotency and conflict/duplicate rejection."""
from pathlib import Path
import importlib.util, json, shutil, tempfile

repo = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preid', repo / 'scripts/apply-phy-pre-id-reset.py')
preid = importlib.util.module_from_spec(spec); spec.loader.exec_module(preid)
meta = preid.meta
with tempfile.TemporaryDirectory(prefix='xg-preid-') as temp:
    root = Path(temp); core = root / meta['core_patch']; core.parent.mkdir(parents=True)
    shutil.copyfile(repo / 'tests/fixtures/phy-pre-id-baseline.patch', core)
    dts = root / meta['dts']; dts.parent.mkdir(parents=True)
    original = '\n'.join('''phy%s: ethernet-phy@%s {
        reg = <%s>;
        reset-gpios = <&en7581_pinctrl %s GPIO_ACTIVE_LOW>;
        reset-assert-us = <200000>;
        reset-deassert-us = <200000>;
        tx-polarity = <PHY_POL_INVERT>;
        rx-polarity = <PHY_POL_INVERT>;
};''' % (addr, addr, addr, gpio) for addr, gpio in meta['phys'].items())
    original += '\nother: ethernet-phy@f { reset-assert-us = <1000000>; };\n'
    dts.write_text(original)
    preid.install(root); first = dts.read_text()
    assert first.count('reset-before-id-read;') == 2
    assert first.replace('        reset-before-id-read;\n', '') == original, 'Unrelated board settings changed'
    preid.install(root); assert dts.read_text() == first
    assert json.loads((root / 'files/etc/xg2010g-phy-pre-id-reset.json').read_text()) == meta
    for bad in [original.replace('200000', '100000', 1), original.replace('29 GPIO', '28 GPIO'),
                first.replace('reset-before-id-read;', 'reset-before-id-read = <0>;', 1)]:
        dts.write_text(bad)
        try: preid.install(root)
        except AssertionError: pass
        else: raise AssertionError('Conflicting board setup accepted')
        assert dts.read_text() == bad, 'Partial edit on rejection'
    dts.write_text(original)
    duplicate = core.with_name('706-duplicate-preid.patch'); shutil.copyfile(core, duplicate)
    try: preid.install(root)
    except AssertionError: pass
    else: raise AssertionError('Duplicate core implementation accepted')
    duplicate.unlink(); core.write_text(core.read_text() + '\nmodified\n')
    try: preid.install(root)
    except AssertionError: pass
    else: raise AssertionError('Unreviewed core patch accepted')
print('PASS: only PHY5/8 opt in; GPIO/timing/polarity preserved; repeat install stable; conflicts and duplicate/unreviewed core rejected. No device CRC claim.')
