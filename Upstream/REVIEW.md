# XG2010G integration review 2026-10-27

This build retains 80e27f7's Linux 6.18.55, NPU 1456-62, guarded PPE path
(949–954), reliability fixes (930–938), RTL826x PHY fixes, CPU policy,
R68 PON driver and MWAN4 routing/default-off behavior.

The only Airoha PPE executable source addition in the maintenance patches is
accepting the flowtable priority action described by upstream patch 957.
No binding-rate, packet-size threshold, ageing or table-statistics change is
used to inflate BND. Not all packets can become bound hardware flows.

955 revokes ordinary direct-xmit flowtable entries when the destination moves
to another bridge port; 956 advertises VLAN/CVLAN matches; 957 preserves the
flow's priority. Sources and exact hashes are in SOURCE.json. The existing
DSCP tuple member required one context adaptation in 955. All three patches
applied with fuzz=0, reversed/reapplied byte-identically, and 16 AArch64 objects
compiled with KCFLAGS=-Werror. The actual prepared binding/RCU/lifetime
function fixtures and the new FDB callback fixture passed. These checks do
not establish hardware performance, DHCP fault recovery or absence of bugs.

The new horizontal optics card comes from naoki66/OpenWrt_ONU_CONFIG 3cb1356.
Its AST matches the read-only snapshot of the user's current router card;
the port card also matches the retained LuCI feed. Order is ports, PON,
network. Local adaptation only adds full-width integration and a fresh module
name. Aurora/Argon desktop/mobile, polling, hide/show and dark-mode checks
passed in 12 browser cases. Optical severity thresholds are upstream display
defaults, not a diagnosis of this particular optical module.

NPU LuCI is naoki66/luci-app-airoha c0abc62, local r908. Existing complete
export, counter metadata and shared CPU policy adapters remain. The first-boot
RPC recovery is a separate bounded one-shot and cannot reapply CPU policy.
The DNS guard handles duplicate UCI/base log-facility before dnsmasq startup,
with a one-time backup and no restart loop. This is a verified configuration
failure mode, not proof of the cause of the other firmware's LAN1/LAN2 outage.

Screenshot plugin sources are recorded in Packages/Extras/SOURCE.json.
The actual current router confirms that “组播转换” is msd_lite. Watchcat has
no automatic reboot rule on first install. PBR, msd_lite, udpxy, UPnP and
Pushbot retain inactive defaults. MWAN4 remains explicit-start. Do not run
competing policy-routing configurations without reviewing their rules.

Host-cache reuse is exact-key only. Firmware builds let make select required
Go/Rust dependencies instead of always prebuilding both; warmup-only retains
prebuilding. No stamp is touched to bypass dependency checks. Cache assets
from other runs are preserved. Actual timing gains require CI evidence.

This branch builds the requested naoki UI image; no router is flashed or
reconfigured, and no shutdown or recurring monitor is enabled.

Per the user's final selection, EIP93 keeps the current router/upstream
algorithm-derived "Active sessions" display. The old two-field probe fixture
is updated to validate the three fields, per-block baseline subtraction,
zero clipping and exclusion of unrelated software algorithms. It is still a
derived indicator, not measured hardware utilization or crypto throughput.
PSE register read failure remains null rather than a fabricated zero.
