# PPE counter schema 2

AN7581's NPU statistics are indexed by hardware slot. An UNB key may reuse a
slot whose previous binding left nonzero counters; those numbers do not belong
to the current unbound connection. Unbound NAT/L2 union fields are also not
valid binding results.

The public packets/bytes fields therefore contain decimal strings only for a
BND entry with reported counter capability and a supported counter layout.
Other states, native L2B and unavailable counters return null with counter_status.
A genuine zero remains "0". Original slot values and rewrite/L2 fields remain
under raw for diagnostics; IB1, IB2 and data are also exported without conversion.
The UI renders unavailable counters as N/A, including legacy cached UNB replies.

Paginated exports retain one boot ID and capture uptime from the saved snapshot.
This does not make the sequential hardware read atomic or prove that a matched
tuple was never rebuilt between snapshots. Slot sums/BND counts are not an
overall offload percentage.

Neither direction nor a fake-IP address is an exclusion criterion here. Forwarded
WAN return traffic and LAN bridge traffic retain their actual BND records. No
binding threshold, timeout, forwarding policy, NPU firmware or driver is changed.

Validation: Runtime/tests/runtime-test.py and Runtime/tests/export-test.js cover
slot reuse, null vs genuine zero, uint64 precision, unsupported/capability cases,
inbound/fake-IP records and complete snapshot pagination/boot consistency.
