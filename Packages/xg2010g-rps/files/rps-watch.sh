#!/bin/sh
# Recover driver queue resets after late initialization or service restarts.
while :; do
	/usr/bin/rps-guard.sh
	sleep 5
done
