#!/usr/bin/env python3
"""Verify the PPE v2 patch in the configured and compiled firmware kernel."""
import argparse
import re
from pathlib import Path

MARKERS = {
    "airoha_eth.h": ("bool flow_stats_cap;",),
    "airoha_npu.c": ("if (!ppe_data->stats_info.npu_stats_addr)", "err = -ENOSPC;"),
    "airoha_ppe.c": (
        "if (!ppe->flow_stats_cap)", "NPU refused flow stats (%d)",
        "ppe->flow_stats_cap = false;", "!airoha_is_7583(eth)",
        "airoha_fe_clear(eth, PSE_FC_CFG, PSE_PORT6_SHARE_DIS)",
    ),
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
        if not re.match(r"^6\.18\.\d+(?:[.~+-]|$)", packages.get("kernel", "")):
            raise ValueError(f"{manifest.name}: expected kernel 6.18.x")
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
    print(f"PPE v2 fallback verified in the compiled {kernel.name} kernel and firmware manifest")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", required=True, type=Path)
    parser.add_argument("--build-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        check(args.manifest_dir, args.build_dir)
    except (ValueError, OSError) as error:
        parser.exit(1, f"PPE build check failed: {error}\n")


if __name__ == "__main__":
    main()
