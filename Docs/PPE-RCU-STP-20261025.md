# PPE RX bridge STP accessor correction

On the shipped f724c96 image, the bridge cache-miss preparation path produced
`RTNL: assertion failed at net/bridge/br_stp.c (77)` from threaded RX/NAPI.
`br_port_get_stp_state()` requires RTNL; the caller only holds RCU. The former
host fixture returned a state without modeling this API contract and missed it.

Patch 954 adds a separate RCU STP accessor. It checks bridge membership,
dereferences the port under the caller's RCU read section and reads the state
with `READ_ONCE`. Both ingress and egress keep the existing forwarding-state
requirement. The packet path does not acquire a sleeping RTNL lock. The original
RTNL accessor and its existing callers are unchanged.

The prepared-function tests now use the actual new accessor and check the RCU
contract. They reject the previous production RX body, blocked/missing ingress
and egress ports, and an accessor call outside the modeled read section.
All existing filtering, VLAN, isolation, local/control-packet exclusions,
generation fencing and owned-entry reclamation remain in place.

The existing read-only PPE `config` output also reports boot readiness,
flowtable references, policy/topology fences and fallback fault state. These are
independent state reads, not an atomic admission decision. No per-packet tracing,
threshold, ageing, artificial BND count or forwarding setting is added.

The one-hour passive observation already showed increasing hardware counters
and some bound LAN-to-LAN IPv4 flows. Thus the port was not wholly inactive.
This correction addresses a confirmed API-contract defect; it does not establish
the cause of every unbound flow, an increase to another image's BND count, or the
cause of the other naoki66 image's no-IP outage. Those require target-device
validation under comparable traffic after a user-authorized flash.

The board/PHY/DHCP/CPU/PON/MWAN4 configuration, NPU1456 pair, EIP93 stack and
pinned r907 LuCI sources remain unchanged. Object compilation, complete image
compilation, offline delivered-image verification and device validation are
reported as separate stages.
