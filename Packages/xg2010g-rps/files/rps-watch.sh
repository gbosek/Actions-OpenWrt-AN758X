#!/bin/sh
# Recover driver queue resets after late initialization or service restarts.
# An advisory lock is released by the kernel when the watcher exits.
# The package requires flock; independent/manual launches cannot race procd.
exec 9>/var/run/xg2010g-rps-watch.lock || exit 1
flock -n 9 || exit 0
while :; do
	/usr/bin/rps-guard.sh
	sleep 5
done
