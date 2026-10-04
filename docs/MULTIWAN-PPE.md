# XG2010G Dynamic Multi-WAN with PPE/NPU

## Goal

The first milestone is **dynamic dual-WAN**, not a fixed PON+EN8811H layout.

Any eligible physical routed port may be selected as WAN. The system must
assign the two AN7581 hardware WAN selectors dynamically and both active WANs
must retain PPE/NPU hardware flow offload.

A configuration is not considered successful if the second WAN silently falls
back to CPU software forwarding.

## Non-goals for milestone 1

- Do not change the existing main branch / known-good build path.
- Do not hard-code EN8811H, RTL8261N, or PON as WAN1.
- Do not change ClankerNPU mailbox ABI yet.
- Do not attempt 3/4-WAN until two hardware WAN slots are proven stable.

## Hardware facts

AN7581 FE exposes two WAN selectors in REG_FE_WAN_PORT:

- WAN0: bits 4:0
- WAN1: bits 12:8
- WAN1 enable: bit 16

The current upstream/PonWrt GDM2-loopback code programs WAN0 and historically
clears WAN1 at the same time. The experimental queue first stops that behaviour
so later code can own WAN1 independently.

## Milestone 1 acceptance

Both selected WANs must pass all of the following:

1. Correct physical ingress/egress path.
2. NAT/route flow creates FOE BIND entries.
3. PPE/NPU counters increase in both directions.
4. CPU load stays low versus software forwarding.
5. PPPoE/VLAN works when used by the selected WAN.
6. mwan3 connection policy selects the expected egress device before offload.
7. WAN failover flushes/rebuilds stale hardware flows.
8. Changing the selected physical WAN does not require rebuilding firmware.

## Development order

1. Preserve and expose both hardware WAN selectors.
2. Add explicit per-netdev HW-WAN slot state.
3. Add a two-slot allocator (WAN0/WAN1).
4. Remove the single-WAN/GDM2-loopback assumption for slot 1.
5. Add userspace role control and automatic OpenWrt integration.
6. Validate PPE/NPU offload on two arbitrary physical WAN choices.
7. Only then investigate direct-PPE third/fourth WAN paths.

## Debug interface

The experimental patch queue extends `/sys/kernel/debug/ppe/config` with
decoded WAN selector state so field testing can verify the hardware register,
not merely LuCI/UCI configuration.
