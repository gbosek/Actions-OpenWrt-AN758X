# Correct the PonWrt temperature overlay

Build 38405331049 contains the requested PPE v2 patch. The build log verifies the compiled Linux 6.18.52 PPE driver and firmware manifest. Direct extraction of the published sysupgrade image confirms that the four-core CPU RPC and renderer are present.

Temperature integration did not work: provenance installation creates files/etc before the workflow copies its overlay. `cp -r "$GITHUB_WORKSPACE/files" files` therefore nested the overlay under files/files, installing /files/sbin/tempinfo instead of the /sbin/tempinfo path used by LuCI. The published image has no /sbin/tempinfo.

Copy the overlay's contents with `cp -a "$GITHUB_WORKSPACE/files/." files/`. Keep the existing executable-bit restoration. The post-build check now requires an executable /sbin/tempinfo matching the repository, all four sensor labels, the correct RPC call path, and no nested temperature script.

CPU is read from thermal_zone0; PON from ponctl; LAN1 and LAN2 from the corresponding PHY hwmon sensors. Sensors appear only when valid readings are available. Device readings and dual-WAN hardware offload remain subject to real hardware testing.
