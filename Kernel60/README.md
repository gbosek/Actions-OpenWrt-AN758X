# XG2010G Linux 6.18.60 selective maintenance

Baseline: successful build 40740596825 / 723fd37aa041d90f139d890a181e8d224d014bcf. Keep the pinned PonWrt a57faf9 base and install all original layers first. `diy-part2.sh` then applies the exact final `pon-6.18.55-to-6.18.60.patch`, checked against complete pre/post file hashes. Historical 6.18.54/55 installers remain prerequisites, not the delivered kernel.

The official Linux 6.18.60 archive hash is pinned. Native stable fixes (flowtable pending/GC synchronization, failed nft expression reference release, VLAN encapsulation underflow, networking/page_pool/GSO fixes) are not added again as separate patches. The patch queue was rebased with exact contexts and tested on a clean official archive at fuzz=0.

Selected new work:

- 961: propagate complete-forward-path errors; mask VID instead of PCP/DEI bits in routed and custom bridge tuple parsing; reset nested-bridge port-VLAN scope. Adapt OpenWrt 2d7e2a4a / be75fbfa / 09fe0f81 to the existing path and guarded fallback APIs.
- Five upstream netdev LED trigger lifetime, locking and sysfs-race fixes.
- DNSmasq 2.93 security fixes, ubus type-name lifetime/UAF/idle reconnect fixes; keep the original init, DHCP configuration and logging guard.
- Odhcp6c reconnect after ubusd restart; minimal PPP shell argument quoting. No PPP non-root/ujail migration.
- FullCone attribute numbering/range/flags and 32-bit port-range handling, matching the retained nftables/libnftnl ABI. Keep the existing 6.12+ API compatibility patch.
- Musl regcomp integer-overflow fix. Toolchain cache identity now includes patch files so a changed security patch cannot reuse an old toolchain unnoticed.

Preserve original PPE/NPU binding thresholds/ageing/statistics, 1456-62 microcode, PON R68, board/PHY/pre-ID reset, CPU OPPs, PON+8 PPPoE handling, MWAN4/LuCI Chinese pair/default-off/no presets, Argon 3.1 and clients memory/history fixes. Main Airoha PPE, Ethernet and NPU prepared C sources match the baseline byte-for-byte. Do not replace the board with LEDE's PON-disabled router DTS or import the new GDM/LRO architecture wholesale.

One genuinely duplicate PCS bounds-check hunk was removed from 606 because 604 already provides it; all four port-count assignments remain. Existing queue hunks were rebased around stable ARP address snapshots, IPv6 payload length, fq_codel quantum and PHY/PCS/PON context; the native fixes are retained. Some original .55 queue patches already needed fuzz in prior CI. The .60 rebases encode the exact intended result instead of inheriting that fuzz.

`SOURCE.json` contains complete pre/post file hashes and upstream provenance. Local evidence is in the parent output directory: strict forward-only 636-patch firmware replay plus 454-patch generic headers replay and ARM64 headers_install; actual flow-path/FDB/guard/PHY/PPPoE function tests; ARM64 driver objects and DNS/DHCPv6 binaries/FullCone/regex objects. These are not a complete firmware or hardware test. CI must still build and validate the exact FIT, rootfs, ABI, packaged kernel and file provenance. LAN stability, CRC behavior and throughput require subsequent device validation; BND count alone is not throughput or an offload percentage.

Failure follow-up: the first local --batch-only check auto-reversed native EG060W support. Its 637-patch claim is superseded. Duplicate782 is now removed from the migration; test-patch-queue.py rejects native duplicates and replays generic and target queues forward-only before CI builds the toolchain. See 编译失败修复-20261101.md.
