#!/bin/sh
# The standard packet_steering service calls this on boot, config reload,
# and interface events. A single writer avoids racing the generic allocator.
board="$(cat /tmp/sysinfo/board_name 2>/dev/null)"
if [ "$board" = "gemtek,xg2010g" ] && [ "${1:-0}" = "2" ]; then
	exec /usr/bin/rps-tune.sh
fi

# Preserve normal steering and the user's off switch for other cases.
flows="$(uci -q get 'network.@globals[0].steering_flows')"
if [ "${flows:-0}" -gt 0 ] 2>/dev/null; then
	exec /usr/libexec/network/packet-steering.uc -l "$flows" "${1:-0}"
fi
exec /usr/libexec/network/packet-steering.uc "${1:-0}"
