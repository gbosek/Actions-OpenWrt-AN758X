#!/bin/sh
# Restore observed queue resets while respecting the packet-steering switch.
board="$(cat /tmp/sysinfo/board_name 2>/dev/null)"
[ "$board" = "gemtek,xg2010g" ] || exit 0
[ "$(uci -q get 'network.@globals[0].packet_steering')" = "2" ] || exit 0

drift=0
for queue in /sys/class/net/*/queues/rx-*; do
	[ -d "$queue" ] || continue
	if [ -w "$queue/rps_cpus" ]; then
		mask="$(cat "$queue/rps_cpus" 2>/dev/null)"
		case "$mask" in f|0000000f) ;; *) drift=1 ;; esac
	fi
	if [ -w "$queue/rps_flow_cnt" ]; then
		count="$(cat "$queue/rps_flow_cnt" 2>/dev/null)"
		[ "$count" = "1024" ] || drift=1
	fi
done
if [ -w /proc/sys/net/core/rps_sock_flow_entries ]; then
	entries="$(cat /proc/sys/net/core/rps_sock_flow_entries 2>/dev/null)"
	[ "$entries" = "4096" ] || drift=1
fi
[ "$drift" = "1" ] || exit 0
logger -t rps-guard 'RPS/RFS drift detected; restoring XG2010G settings'
/usr/bin/rps-tune.sh
