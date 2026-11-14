	# DT is authoritative even after the boot log wraps; ignore the old empty cache.
	local mem_cache="/tmp/npu-mem-regions-v2.json"
	local mem_tmp="" regions="[]"
	if [ -f "$mem_cache" ]; then
		regions=$(cat "$mem_cache" 2>/dev/null)
	else
		regions=$(/usr/libexec/airoha-npu-memory 2>/dev/null)
		local mem_info=""
		case "$regions" in
			'[]'|'') mem_info=$(dmesg 2>/dev/null | grep "reserved mem.*npu" | head -4) ;;
		esac
		if [ -n "$mem_info" ]; then
			regions=$(echo "$mem_info" | awk '
			BEGIN { printf "[" }
			{
				if (NR > 1) printf ","
				match($0, /0x[0-9a-fA-F]+\.\.0x[0-9a-fA-F]+/)
				range = substr($0, RSTART, RLENGTH)
				split(range, a, "\\.\\.")
				match($0, /\([0-9]+ [KMG]i?B\)/)
				size = substr($0, RSTART+1, RLENGTH-2)
				match($0, /non-reusable [^ ]+/)
				name = substr($0, RSTART+13)
				gsub(/@.*/, "", name)
				printf "{\"name\":\"%s\",\"start\":\"%s\",\"end\":\"%s\",\"size\":\"%s\"}", name, a[1], a[2], size
			}
			END { printf "]" }
			')
		fi
		# tmp+mv rather than `>`: the redirect truncates the live cache before
		# writing it, so a second rpcd child reading at that instant gets an
		# empty file - the very input the guard below exists for.
		case "$regions" in
			'['*']') ;;
			*) regions='[]' ;;
		esac
		# Do not cache a failed/empty discovery indefinitely.
		[ "$regions" != '[]' ] && mem_tmp=$(mktemp /tmp/npu-mem-regions.XXXXXX 2>/dev/null)
		if [ -n "$mem_tmp" ]; then
			printf '%s' "$regions" > "$mem_tmp" 2>/dev/null &&
				mv -f "$mem_tmp" "$mem_cache" 2>/dev/null || rm -f "$mem_tmp"
		fi
	fi
	# The cached text is spliced into the reply as-is, so anything that is not
	# a JSON array - an empty or truncated cache, a hand-edited file - would
	# emit `"memory_regions":,` and make the whole RPC unparseable, taking
	# getDashboard down with getStatus.
	case "$regions" in
		'['*']') ;;
		*) regions='[]' ;;
	esac

