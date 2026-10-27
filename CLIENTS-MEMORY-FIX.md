# Clients collector repair

The pinned upstream `clients-probe` called `index(text, needle, start)` as though
ucode accepted a third start-offset argument. That argument is ignored. The
conntrack parser repeatedly appended the first tuple until memory exhaustion.

Search an explicit string suffix, advance monotonically, and accept at most the
original/reply tuples. Missing accounting must not borrow counters from the next
direction. The old actual function exhausted a 32 MiB isolated process while
parsing one ordinary connection; the repaired function passes 17 cases and
10,000 repeat parses within the same limit.

The DNS collector had the analogous `fs.readfile(path, count, offset)` error.
Use a seekable handle and a 64 KiB batch. After a complete batch is archived,
rotate only the fully consumed default RAM log at 1 MiB, retaining the latest
1,000 archived rows. Verify inode/device identity, refuse symlinks and leave
custom log paths alone. This is a recent-query display, not a lossless DNS audit
log; size checks and truncation are not an atomic handoff with dnsmasq's writer.
Tests cover offset reads, EOF, bounds, rotation and symlink refusal.

Mount current zoneinfo paths into the existing dnsmasq jail. A firmware using
`/etc/localtime` must not leave the jailed daemon on UTC while the collector
parses local time. Preserve the existing jail and duplicate-log-facility guard.
First boot fills only missing DNS logging options for enabled collectors,
preserving explicit choices. It does not change routing or WAN policies.

Package release: `luci-app-clients 0.1.0-r3`. The workflow verifies exact staged
helpers and runs the real ucode regression under memory/time limits. The PPE/NPU
binding method, packet thresholds, PHY and board layout are unchanged.
