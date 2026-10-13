#!/bin/sh
# Restore observed queue resets while respecting the packet-steering switch.
IFS= read -r board < /tmp/sysinfo/board_name 2>/dev/null || exit 0
[ "$board" = "gemtek,xg2010g" ] || exit 0
[ "$(uci -q get 'network.@globals[0].packet_steering')" = "2" ] || exit 0

drift=0
for queue in /sys/class/net/*/queues/rx-*; do
	[ -d "$queue" ] || continue
	if [ -w "$queue/rps_cpus" ]; then
		IFS= read -r mask < "$queue/rps_cpus" || mask=
		case "$mask" in f|0000000f) ;; *) drift=1 ;; esac
	fi
	if [ -w "$queue/rps_flow_cnt" ]; then
		IFS= read -r count < "$queue/rps_flow_cnt" || count=
		[ "$count" = "1024" ] || drift=1
	fi
done
if [ -w /proc/sys/net/core/rps_sock_flow_entries ]; then
	IFS= read -r entries < /proc/sys/net/core/rps_sock_flow_entries || entries=
	[ "$entries" = "4096" ] || drift=1
fi
[ "$drift" = "1" ] || exit 0
logger -t rps-guard 'RPS/RFS drift detected; restoring XG2010G settings'
/usr/bin/rps-tune.sh
