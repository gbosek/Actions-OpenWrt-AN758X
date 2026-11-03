# Minimal XG2010G maintenance, 2026-11-04

These two review deltas are incorporated into the single existing `source-patches/pon-6.18.55-to-6.18.60.patch`. They are not applied a second time. Exact path/hash provenance is in `Kernel60/SOURCE.json`.

- [OpenWrt 2cac72feed9460fd9303b66a11feaed89fb854fe](https://github.com/openwrt/openwrt/commit/2cac72feed9460fd9303b66a11feaed89fb854fe): publish the local DNS resolver configuration with rename and keep a stable resolver-directory link. Retain the separate ISP-generated `resolv.conf.auto` consumed by the MWAN4 DNS guard. Do not include the unrelated capability/procd dependency update.
- [OpenWrt 5b3efb652f816d8024801e0b165532e20654a678](https://github.com/openwrt/openwrt/commit/5b3efb652f816d8024801e0b165532e20654a678): save an error code before freeing an existing block-NVMEM provider allocation. No new provider, module or board configuration is added. Current XG2010G MTD/UBI providers do not demonstrate that this error path was being triggered.

For stability and traceability, leave the larger QDMA/LRO and DSA host-FDB changes for separate scoped work. Preserve PON, PHY, CPU, MWAN4, DHCP/DNS logging choices and PPE/NPU safety guards. Neither fix establishes a cause or cure for LAN1 loss, and offline tests cannot establish hardware stability.
