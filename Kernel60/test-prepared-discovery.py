#!/usr/bin/env python3
"""Exercise the real source gate before/after configure and with invalid trees."""
from pathlib import Path
import json, shutil, subprocess, sys, tempfile

R = Path(__file__).resolve().parents[1]
S, K = (Path(p).resolve() for p in sys.argv[1:])
meta = json.loads((R/'Kernel60/SOURCE.json').read_text())
offload = json.loads((R/'Offload/SOURCE.json').read_text())
files = set(meta['prepared_sources']) | set(offload['expected_prepared_sources'])
files.add('drivers/usb/serial/option.c')
cases = []
with tempfile.TemporaryDirectory(prefix='kernel60-prepared-discovery-') as d:
    root = Path(d)
    # Reuse the exact migration/queue files without modifying the source.
    for name in {Path(row['path']).parts[0] for row in meta['files']} | {'target'}:
        (root/name).symlink_to(S/name, target_is_directory=True)
    parent = root/'build_dir/target-aarch64_fixture/linux-airoha_an7581'
    kernel = parent/'linux-6.18.60'
    for name in files:
        dest = kernel/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(K/name, dest)

    def check(label, expected, diagnostic=None):
        result = subprocess.run([sys.executable, str(R/'Kernel60/check-prepared.py'), str(root)], text=True, capture_output=True)
        assert (result.returncode == 0) == expected, (label, result.stdout, result.stderr)
        if diagnostic:
            assert diagnostic in result.stderr, (label, result.stderr)
        cases.append(label)

    assert not (kernel/'.config').exists()
    check('prepared source without .config', True)
    (kernel/'.config').write_text('# configuration is checked by post-build gates\n')
    check('configured source with .config', True)
    duplicate = root/'build_dir/target-second/linux-airoha_an7581/linux-6.18.60'
    duplicate.parent.mkdir(parents=True)
    duplicate.symlink_to(kernel, target_is_directory=True)
    check('ambiguous prepared sources rejected', False, 'found 2')
    duplicate.unlink()
    renamed = parent/'linux-6.18.55'
    kernel.rename(renamed)
    check('wrong kernel version rejected', False, 'found 0')
    renamed.rename(kernel)
    target = kernel/'drivers/net/ethernet/airoha/airoha_ppe.c'
    target.write_bytes(target.read_bytes()+b'\n/* unreviewed source drift */\n')
    check('exact driver hash drift rejected', False, 'airoha_ppe.c')
print(json.dumps({'status':'passed','cases':cases,'scope':'Actual complete-source gate, not compilation or hardware validation'}))
