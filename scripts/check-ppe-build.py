#!/usr/bin/env python3
"""Reject an XG2010G artifact built without the required PPE implementation."""
import argparse
import hashlib
import re
from pathlib import Path

PACKAGES = (
    "airoha-en7581-npu-firmware", "kmod-nf-flow", "kmod-nft-offload",
    "bridger", "tc-full", "ethtool-full",
)
FIRMWARE_DIGESTS = {
    "en7581_npu_rv32.bin": "6e7b9cb9769398d5c0a603d758626719ee83610e0dd2a5bc0b66258e2ad1057f",
    "en7581_npu_data.bin": "0e742e7bef0d8f4c1537d7c17de9b601274e42b18660dfde6deba81ac395c761",
}
SOURCE_MARKERS = {
    "airoha_eth.h": ("struct airoha_l2_flow_key", "bool flow_stats_cap;"),
    "airoha_ppe.c": (
        "eth->ports[AIROHA_GDM2_IDX - 1]",
        "airoha_ppe_parse_l2_key", "airoha_ppe_l2_key_from_skb",
        "sizeof(struct airoha_l2_flow_key)",
    ),
    "airoha_ppe_debugfs.c": (
        "setup_attempts:", "tc_replace_failed:", "egress_pse_port=%u",
        '"available" : "unavailable"',
    ),
    "airoha_npu.c": ("if (!ppe_data->stats_info.npu_stats_addr)",),
}


def check(manifest_dir, build_dir):
    manifests = sorted(manifest_dir.glob("*.manifest"))
    if not manifests:
        raise ValueError(f"no firmware manifest in {manifest_dir}")
    for manifest in manifests:
        packages = dict(re.findall(r"^(\S+) - (.+)$", manifest.read_text(), re.M))
        missing = [p for p in PACKAGES if p not in packages]
        if missing:
            raise ValueError(f"{manifest.name}: missing packages: {', '.join(missing)}")
        if not re.match(r"^6\.18\.\d+(?:[.~+-]|$)", packages.get("kernel", "")):
            raise ValueError(f"{manifest.name}: expected kernel 6.18.x")
        print(f"PPE manifest OK: {manifest.name}")

    kernels = [p.parent for p in build_dir.glob("**/linux-6.18.*/.config")
               if (p.parent / "drivers/net/ethernet/airoha/airoha_ppe.c").is_file()]
    if len(kernels) != 1:
        raise ValueError(f"expected one prepared 6.18 kernel, found {len(kernels)}")
    kernel = kernels[0]
    config = (kernel / ".config").read_text()
    for symbol in ("CONFIG_NET_AIROHA", "CONFIG_NET_AIROHA_NPU"):
        if not re.search(rf"^{symbol}=[ym]$", config, re.M):
            raise ValueError(f"{kernel}: {symbol} disabled")
    if not re.search(r"^CONFIG_NET_AIROHA_FLOW_STATS=y$", config, re.M):
        raise ValueError(f"{kernel}: flow statistics disabled")
    driver = kernel / "drivers/net/ethernet/airoha"
    for name, markers in SOURCE_MARKERS.items():
        text = (driver / name).read_text()
        for marker in markers:
            if marker not in text:
                raise ValueError(f"{name}: PPE patch marker missing: {marker}")
    print(f"PPE prepared kernel OK: {kernel.name}")
    for name, expected in FIRMWARE_DIGESTS.items():
        files = list(build_dir.glob(f"target-*/root-*/lib/firmware/airoha/{name}"))
        if not files:
            raise ValueError(f"installed rootfs missing {name}")
        for firmware in files:
            if hashlib.sha256(firmware.read_bytes()).hexdigest() != expected:
                raise ValueError(f"{firmware}: firmware differs from the reviewed 1456 ABI")
        print(f"PPE firmware SHA-256 OK: {name}")


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
