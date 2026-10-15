#!/bin/sh
_run_with_deadline() {
	local seconds="$1"
	local tag="$2"
	local base output done child_file
	local worker timer child rc
	shift 2

	# /tmp is world-writable and the caller (rpcd) runs as root: a name built
	# from $$ is guessable, and a symlink planted there would be followed by
	# the redirections below. mktemp gives an unpredictable base instead.
	base="$(mktemp "/tmp/airoha-common.${tag}.XXXXXX" 2>/dev/null)" || return 1
	rm -f "$base"
	output="$base.out"
	done="$base.done"
	child_file="$base.child"

	(
		"$@" >"$output" 2>/dev/null &
		child=$!
		printf '%s\n' "$child" >"$child_file"
		wait "$child"
		printf '%s\n' "$?" >"$done"
	) >/dev/null 2>&1 &
	worker=$!

	sleep "$seconds" >/dev/null 2>&1 &
	timer=$!

	wait -n 2>/dev/null
	if kill -0 "$worker" 2>/dev/null && kill -0 "$timer" 2>/dev/null; then
		local elapsed=0
		while [ "$elapsed" -lt "$seconds" ] && [ ! -e "$done" ]; do
			sleep 1
			elapsed=$((elapsed + 1))
		done
	fi

	if [ -e "$done" ]; then
		kill "$timer" 2>/dev/null; wait "$timer" 2>/dev/null
		wait "$worker" 2>/dev/null
		read -r rc <"$done" 2>/dev/null
		if [ "${rc:-1}" -eq 0 ]; then
			[ ! -s "$output" ] || cat "$output"
			rm -f "$output" "$done" "$child_file"
			return 0
		fi
		rm -f "$output" "$done" "$child_file"
		return 1
	fi

	[ -s "$child_file" ] && { read -r child <"$child_file" 2>/dev/null; kill -9 "$child" 2>/dev/null; }
	kill -9 "$worker" 2>/dev/null; wait "$worker" 2>/dev/null
	kill "$timer" 2>/dev/null; wait "$timer" 2>/dev/null
	rm -f "$output" "$done" "$child_file"
	return 124
}
