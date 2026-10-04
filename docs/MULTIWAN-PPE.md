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

## Original vendor reference and evidence limits

The Airoha SDK snapshot contains `FE_API_SET_WAN_PORT_7516(wan1_en, wan1_port,
wan0_port)` and `fe_api_set_wan_port_7516()`, which composes both selector values
and writes `FE_WAN_PORT` in one operation. Treat this as a vendor design
reference, not proof that the XG2010G stock image calls this API: the SDK header
selects different WAN1 bit offsets under legacy SoC build macros, and this
snapshot's exact XG2010G build configuration has not been established. The Linux
EN7581 register definition independently confirms the WAN0/WAN1 bit fields
above and is the offset source for the 6.18 driver work.

The vendor HWNAT sources also carry per-interface WAN accounting/meter indices
(up to eight logical indices). Those indices are accounting metadata and must
not be confused with the two FE WAN selectors or proof of multiple hardware
egress paths. The stock boot log proves NPU, HWNAT/FOE, and QDMA initialization,
but the extracted sample has no WAN1 register snapshot or per-flow BIND/counter
capture. Record stock dual-WAN PPE use as **plausible, not confirmed**.

The upstream Linux 6.18 NPU driver initializes PPE with the Ethernet WAN mode;
that selects the WAN transport mode, not a WAN-slot allocator. The upstream FE
register definition has WAN1 fields, while the current `airoha_eth` driver does
not use them. The GDM2 loopback setup also used to clear WAN1 as it rewrote
WAN0. Patches 929/933 address register ownership and add a runtime WAN1 selector,
but 933 only adds selector ownership/control; it does not itself implement
mwan3 policy integration. #16 has not yet demonstrated that WAN1-selected
traffic binds to FOE and uses the intended PPE/PSE/GDM egress and NBQ/queue
mapping in both directions.

### Reproduction on the 1456.62 baseline

Keep the 1456.62 firmware and its matching Linux NPU/mailbox driver as the
baseline. Reuse the vendor design idea—two independently selected FE source
ports—but implement the Linux control and flow paths natively:

1. Keep PON as WAN0 and dynamically assign one eligible GDM3/GDM4 netdev's
   `get_sport(port, nbq)` identity to WAN1 without clearing WAN0.
2. Make route/flow offload retain the mwan3-selected output netdev and its
   GDM/NBQ identity in the FOE entry; ensure the WAN1 path reaches its real
   physical egress and the return direction is recognized.
3. Coordinate QDMA queues and source-port forwarding for the chosen WAN, and
   flush/rebuild flows when mwan3 fails over or the WAN role changes.
   Explicitly validate simultaneous PON WAN0 plus Ethernet WAN1: the upstream
   NPU PPE init passes one global `QDMA_WAN_ETHER` mode, not per-slot mode data.
4. Prove WAN1 using matching FOE BIND entries and increasing hardware packet
   and byte counters, decoded PSE/GDM/NBQ destination, the relevant QDMA
   channel/state, and physical-port MIBs in both directions. Do not assume the
   direct-PPE WAN1 route must use the legacy GDM2/QDMA1 path. A set WAN1 bit
   alone is only control-plane evidence.

The one shared NPU/PPE firmware does not need to be duplicated per WAN. The
open issue is whether the host FE/PPE/QDMA programming and flow selection make
each selected WAN's route expressible and correctly installed in FOE.

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


## Milestone 1 direct-PPE WAN1 experiment

The first runtime WAN1 experiment intentionally does **not** migrate the
selected external SerDes netdev to the legacy GDM2-loopback/QDMA1 path.

Reason: EN7581 can expose more than one net_device from a shared GDM using
NBQ/source-port identities. Changing the whole GDM forwarding domain can
disturb a LAN sibling. Instead the experiment:

- keeps native PON/current WAN on hardware WAN0;
- selects one eligible GDM3/GDM4 netdev at runtime as hardware WAN1;
- derives its source-port from `get_sport(port, nbq)`;
- programs only `WAN1_EN/WAN1`;
- keeps PPE egress on the real GDM/NBQ path already supported by the PonWrt
  external-SerDes PPE metadata patches;
- keeps the known-stable CPU miss path until hardware testing proves a QDMA1
  migration is necessary.

Lab control:

```sh
ip link set dev <port> down
ethtool --set-priv-flags <port> hw-uplink on
cat /sys/kernel/debug/ppe/config
ip link set dev <port> up
```

Disable:

```sh
ip link set dev <port> down
ethtool --set-priv-flags <port> hw-uplink off
ip link set dev <port> up
```

This ethtool flag is a bring-up/debug API. UCI/LuCI integration comes only
after the hardware path is proven.

## Hardware-offload proof checklist

A WAN1 result is accepted only when all of these are true:

1. `/sys/kernel/debug/ppe/config` shows WAN1 enabled and its source-port
   matches the selected netdev's reported `sport`.
2. Traffic routed exclusively through WAN1 creates BIND entries in
   `/sys/kernel/debug/ppe/bind`.
3. The matching FOE packet/byte statistics increase while traffic is active.
4. Both LAN->WAN1 and WAN1->LAN/reply traffic remain functional after the flow
   enters BIND state.
5. CPU load is materially lower with hardware flow offload enabled than with
   it disabled at the same throughput.
6. A sibling netdev sharing the same GDM remains a working LAN port.
7. VLAN and PPPoE are tested separately after plain DHCP/static-IP validation.
8. Disabling/reassigning WAN1 does not leave stale traffic blackholes.
9. Only after the above pass do we enable mwan3 and verify policy selection
   occurs before hardware flow installation.

