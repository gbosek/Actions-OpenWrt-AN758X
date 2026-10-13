#!/usr/bin/env python3
"""Install the reviewed XG2010G 6.18 PPE patch queue into a build tree."""
import argparse
import re
import shutil
from pathlib import Path

PATCHES = (
    "931-net-airoha-keep-PPE-offload-when-NPU-refuses-flow-stats.patch",
    "932-net-airoha-use-direct-egress-with-physical-GDM2.patch",
    "933-net-airoha-expose-PPE-setup-and-effective-egress.patch",
    "934-net-airoha-key-L2-flows-by-ingress-and-VLAN.patch",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path.cwd())
    args = parser.parse_args()
    source = args.source.resolve()
    package_root = Path(__file__).resolve().parent.parent
    patch_root = package_root / "kernel-patches/airoha"
    destination = source / "target/linux/airoha/patches-6.18"
    config = source / "target/linux/airoha/an7581/config-6.18"
    if not destination.is_dir() or not config.is_file():
        parser.error("expected an AN7581 source tree with the 6.18 kernel")
    text = config.read_text()
    if not re.search(r"^CONFIG_NET_AIROHA_NPU=[ym]$", text, re.M):
        parser.error("the source configuration does not enable the Airoha NPU")
    # Check the complete queue before changing any destination.
    for name in PATCHES:
        origin = patch_root / name
        if not origin.is_file():
            parser.error(f"missing reviewed patch: {origin}")
        for existing in destination.glob(name[:3] + "-*.patch"):
            if existing.name != name or existing.read_bytes() != origin.read_bytes():
                parser.error(f"conflicting patch order {name[:3]}: {existing}")
    for name in PATCHES:
        shutil.copyfile(patch_root / name, destination / name)
        print(f"PPE patch: {name}")
    text = re.sub(
        r"^(?:# CONFIG_NET_AIROHA_FLOW_STATS is not set|CONFIG_NET_AIROHA_FLOW_STATS=.*)\n?",
        "", text, flags=re.M,
    )
    config.write_text(text.rstrip() + "\nCONFIG_NET_AIROHA_FLOW_STATS=y\n")
    print("AN7581 flow statistics enabled with optional firmware fallback")


if __name__ == "__main__":
    main()
