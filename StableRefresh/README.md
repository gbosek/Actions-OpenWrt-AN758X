# XG2010G 6.18.55 full baseline refresh — 2026-11-09

## Scope

The baseline is the successful October 18 build `a6440d4412a7de08d003afbba1501f0a2e28e980`, not the subsequent reduced-package image. Its delivered ITB SHA256 is `3f4641d2770e6f9dc69e72438c79dcfa1485525ae77b082ad47e01bb9066e1c0`. The base PonWrt source is `a57faf93c6c3638ba3651690228aabaa51d3f235`, with the baseline's Linux 6.18.55 adaptations and driver/PPE/boot/LED fixes retained.

Only the custom overclock injection is removed. Native CPU OPPs remain 500–1200 MHz; no custom CPU-policy helper or >1200 MHz OPP is allowed in the result. This does not claim that all possible stability faults have been fixed.

The full baseline manifest is checked both before compilation (mapping ABI-suffixed installed names to Kconfig symbols) and after compilation (against the actual image manifest). The only replaced standalone package is `luci-app-argon-config`: Argon 3.1.3 supplies that settings interface itself and keeps its translation domain. Disk/partition and Btrfs/F2FS tools, Aurora, WOL, iperf3, IPTV/omcproxy, MWAN4 Chinese translations and baseline board scripts remain selected. `rtp2httpd` 3.16.0 is restored from its upstream package recipe, rather than silently dropping it when absent from the pinned feed.

## Component pins and live updates

`source.json` records Airoha, PON card, official stable Argon v3.1.3, and the r30/r19 MWAN4 source snapshots already installed on the router. Airoha retains the requested raw PPE Ethernet values; unavailable counters use a dash and are not fabricated. The PON card remains r13 because no newer upstream card was found at inspection time. The ONU driver/userspace feed remains the baseline's separate pin; updating a status card does not imply updating the PON driver stack.

The November 9 read-only SSH inspection found current full-LAN Fake-IP no-flow rules plus the November 8 marked LAN-to-LAN no-flow rule. These are captured in `root/etc/firewall.lan-fakeip.nft`, installed as a ruleset-post include so explicit inserts precede `flow add`. Policy table 100, the bypass-source exemption, domestic address sets, existing SNAT/MSS rules and MWAN4 guard are included. The reference MWAN4 file hashes in `source.json` describe the inspected installation, not a promise that newly compiled binaries have those same hashes.

No PPP credentials, password files, proxy subscriptions or complete router configuration dump are included. Existing personal settings still need to be retained during a settings-preserving upgrade or configured separately after a clean flash. The baked policy expects this user's existing .1/.2 topology and bypass MAC/IPv6 link-local address; it is not a generic image for other networks.

## Explicit exclusions

Do not add a daily DNS-log checker. Do not bake automatic disabling of `omcproxy` or `95-xg-ra-refresh`; those remain post-flash manual choices. No live router reboot, restart or firmware write is performed by this build preparation.

## Reproducibility and verification boundary

Feed pins are a historical compatibility snapshot. LuCI's commit is confirmed by the old delivered manifest, but not all original transient feed checkout timestamps were recorded; this is not a claim of bit-for-bit reconstruction. Package closure, native CPU policy and effective live code are checked locally before starting CI. The workflow additionally audits actual FIT region hashes, kernel banner, extracted files, module disassembly and image manifest. An offline audit is not a flash test or a device stability test.

The LuCI firmware description includes `2026.11.09-refresh1` and the actual build date/time. Identify delivered images by build commit, Actions artifact identity and SHA256, not by file size or filename alone.
