# XG2010G guarded PPE bridge fallback

This integrates the naoki bridge cache-miss binding mechanism, its VLAN-aware
forward-path dependency and native AN7581 L2B key preservation into the existing
Linux 6.18.55 runtime-led baseline. The NPU program/data remain 1456-62. Existing
930 native L2B and 931–938 reliability fixes remain; duplicate 9990/9993/9994
implementations are rejected.

Additional safeguards keep local/bridge-MAC traffic, DHCPv4/v6, broadcast,
multicast, ARP/ND, fragmented/truncated/unknown headers on the CPU path. Real
routed L4 flowtable matches retain their original priority. The supplemental
path requires known bridge ports in forwarding state, a valid resolved egress,
and carrier; same-port and isolated-port forwarding are excluded. PON egress
uses the existing routed offload path, because its bearer lookup needs a mutex
unavailable in early RX context.

Only successful TC_SETUP_FT binds activate fallback. Ordinary TC/QoS blocks do
not. RX rechecks this reference under ppe_lock. Fallback-owned hardware slots
are tracked independently, ordinary slot replacement clears that ownership,
and the last flowtable unbind invalidates recorded slots. Cleanup releases the
spinlock and yields between slots. It stops at the first SRAM ACK failure and
reports hardware state as unconfirmed; further fallback stays disabled after
that fault. This is not a claim that broken hardware acknowledged deletion.

## Boundaries

- Early bridge FDB resolution does not prove that arbitrary custom bridge
  forward ACLs permit a packet. This remains a candidate for ordinary trusted
  LAN bridging; do not treat it as verified enforcement for custom bridge ACLs.
- These direct hardware entries are not ordinary parent-linked flowtable
  entries. Hardware aging and last-flowtable cleanup apply; full roaming/FDB
  lifecycle equivalence has not been established by offline checks.
- BND is a hardware table-entry count, not a traffic rate or performance score.
  Control-plane/same-port exclusions deliberately favor CPU correctness.
- No board DTS, PHY programming, port numbering, DHCP/netifd settings or NPU
  microcode are replaced. The PON feed is pinned to the R68 used in the delivered
  20261018 image, preventing an unrelated R69+ update during this build.
- The reported 10G outage in another firmware has no established root cause.
  Compile and regression checks cannot establish physical-port stability.

Run `python3 Offload/tests/check-prepared.py --kernel /path/linux-6.18.55` after
preparing sources. `--compiled` also checks actual AArch64 objects and records
the Image hash when the full image exists. GitHub invokes both gates before
publishing firmware. No test accesses or modifies a router.
