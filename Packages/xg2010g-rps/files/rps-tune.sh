#!/bin/sh
# Parameters from the user's VIKINGYFY 6.18.54 runtime comparison.
[ "$(cat /tmp/sysinfo/board_name 2>/dev/null)" = "gemtek,xg2010g" ] || exit 0

RPS_MASK=f
RFS_ENTRIES=4096
FLOW_CNT=1024

if [ -w /proc/sys/net/core/rps_sock_flow_entries ]; then
	printf '%s\n' "$RFS_ENTRIES" > /proc/sys/net/core/rps_sock_flow_entries
fi

for queue in /sys/class/net/*/queues/rx-*; do
	[ -d "$queue" ] || continue
	if [ -w "$queue/rps_cpus" ]; then
		printf '%s\n' "$RPS_MASK" > "$queue/rps_cpus" 2>/dev/null || :
	fi
	if [ -w "$queue/rps_flow_cnt" ]; then
		printf '%s\n' "$FLOW_CNT" > "$queue/rps_flow_cnt" 2>/dev/null || :
	fi
done
exit 0
