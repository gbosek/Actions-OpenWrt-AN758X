#!/usr/bin/env python3
"""Verify the PPE v2 patch in the configured and compiled firmware kernel."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from check_ppe_functions import check as check_functions

FIRMWARE_SHA256 = {
    'en7581_npu_rv32.bin': '6e7b9cb9769398d5c0a603d758626719ee83610e0dd2a5bc0b66258e2ad1057f',
    'en7581_npu_data.bin': '0e742e7bef0d8f4c1537d7c17de9b601274e42b18660dfde6deba81ac395c761',
}

MARKERS = {
    "airoha_eth.h": ("bool flow_stats_cap;",),
    "airoha_npu.c": ("if (!ppe_data->stats_info.npu_stats_addr)", "err = -ENOSPC;"),
    "airoha_ppe.c": (
        "if (!ppe->flow_stats_cap)", "NPU refused flow stats (%d)",
        "ppe->flow_stats_cap = false;", "!airoha_is_7583(eth)",
        "airoha_fe_clear(eth, PSE_FC_CFG, PSE_PORT6_SHARE_DIS)",
    ),
    "airoha_ppe_debugfs.c": ('flow_stats_cap: %u',),
    "airoha_regs.h": ("#define PSE_PORT6_SHARE_DIS",),
}


def check(manifest_dir, build_dir):
    manifests = sorted(manifest_dir.glob("*.manifest"))
    if not manifests:
        raise ValueError(f"firmware manifest missing: {manifest_dir}")
    for manifest in manifests:
        packages = dict(re.findall(r"^(\S+) - (.+)$", manifest.read_text(), re.M))
        for name in ("airoha-en7581-npu-firmware", "kmod-nf-flow", "kmod-nft-offload"):
            if name not in packages:
                raise ValueError(f"{manifest.name}: missing {name}")
        if not re.match(r"^6\.18\.55(?:[.~+-]|$)", packages.get("kernel", "")):
            raise ValueError(f"{manifest.name}: expected kernel 6.18.55")
    kernels = [p.parent for p in build_dir.glob("target-*/linux-*/linux-6.18.*/.config")
               if (p.parent / "drivers/net/ethernet/airoha/airoha_ppe.c").is_file()]
    if len(kernels) != 1:
        raise ValueError(f"expected one configured 6.18 kernel, found {len(kernels)}")
    kernel = kernels[0]
    config = (kernel / ".config").read_text()
    for symbol in ("CONFIG_NET_AIROHA", "CONFIG_NET_AIROHA_NPU"):
        if not re.search(rf"^{symbol}=[ym]$", config, re.M):
            raise ValueError(f"{kernel}: {symbol} is disabled")
    if not re.search(r"^CONFIG_NET_AIROHA_FLOW_STATS=y$", config, re.M):
        raise ValueError(f"{kernel}: CONFIG_NET_AIROHA_FLOW_STATS is disabled")
    driver = kernel / "drivers/net/ethernet/airoha"
    for filename, markers in MARKERS.items():
        text = (driver / filename).read_text()
        for marker in markers:
            if marker not in text:
                raise ValueError(f"{filename}: missing PPE v2 marker: {marker}")
    for filename in ("airoha_ppe.o", "airoha_npu.o"):
        binary = driver / filename
        if not binary.is_file() or binary.stat().st_size == 0:
            raise ValueError(f"compiled driver object missing: {binary}")
    if b"NPU refused flow stats (%d)" not in (driver / "airoha_ppe.o").read_bytes():
        raise ValueError("the compiled PPE object lacks the NPU-refusal fallback diagnostic")
    assert b'flow_stats_cap: %u' in (driver / 'airoha_ppe_debugfs.o').read_bytes(), 'Compiled capability diagnostic absent'
    regression = check_functions(kernel)
    roots = list(build_dir.glob('target-*/root-airoha'))
    if len(roots) != 1:
        raise ValueError(f'Expected one staged rootfs, found {len(roots)}')
    firmware = {}
    for name, expected in FIRMWARE_SHA256.items():
        path = roots[0] / 'lib/firmware/airoha' / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'1456 firmware identity mismatch: {name}')
        firmware[name] = actual
    repo = Path(__file__).resolve().parents[1]
    patches = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((repo / 'kernel-patches/airoha').glob('93[123]-*.patch'))}
    record = {
        'kernel': kernel.name,
        'flow_stats': True,
        'firmware_version': '2.1.1-TLB7.3.283.1456-62',
        'firmware_sha256': firmware,
        'patch_sha256': patches,
        'driver_object_sha256': {name: hashlib.sha256((driver / name).read_bytes()).hexdigest()
                                 for name in ('airoha_ppe.o', 'airoha_npu.o')},
        'function_regression': regression,
        'scope': 'Build/source/rootfs verification; no router runtime or full lifecycle validation',
    }
    (manifest_dir / 'PPE-BUILD-VERIFICATION.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f"1456 firmware, PPE v2 fallback and candidate functions verified in compiled {kernel.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", required=True, type=Path)
    parser.add_argument("--build-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        check(args.manifest_dir, args.build_dir)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"PPE build check failed: {error}\n")


if __name__ == "__main__":
    main()
