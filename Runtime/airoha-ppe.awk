# Parse the kernel's whitespace-separated FOE debugfs records.
function quote(s,    out, i, c) {
	out = "\""
	for (i = 1; i <= length(s); i++) {
		c = substr(s, i, 1)
		if (c == "\\" || c == "\"") out = out "\\"
		out = out c
	}
	return out "\""
}
function field(name,    i, pos) {
	for (i = 4; i <= NF; i++) {
		pos = index($i, "=")
		if (pos && substr($i, 1, pos - 1) == name)
			return substr($i, pos + 1)
	}
	return ""
}
function counter(name,    value) {
	value = field(name)
	# Preserve 64-bit values without floating-point rounding.
	return value ~ /^[0-9]+$/ ? quote(value) : "null"
}
function bound_field(name) {
	return $2 == "BND" ? quote(field(name)) : "null"
}
function counter_status() {
	# NPU stats live in a separate slot-indexed array. A learned UNB key
	# can reuse a slot whose previous binding left nonzero counters behind.
	if ($2 != "BND") return "not_bound"
	# The retained AN7581 driver has no verified native L2B counter layout.
	if ($3 == "L2B") return "unsupported_l2_counter"
	if (stats_cap != "1") return stats_cap == "0" ? "driver_disabled" : "driver_unreported"
	if (counter("packets") == "null" || counter("bytes") == "null") return "missing_counters"
	return "reported_bound_slot"
}
function hexval(s,    i, c, d, n) {
	n = 0
	for (i = 1; i <= length(s); i++) {
		c = tolower(substr(s, i, 1))
		d = index("0123456789abcdef", c) - 1
		if (d < 0) return -1
		n = n * 16 + d
	}
	return n
}
# This runtime is built for AN7581: each of its two PPE SRAM banks has 8192
# slots. Count all scanned records, independently of UI pagination/limits.
function bucket(idx, state) {
	if (idx < 0) return
	if (idx < 8192) {
		ppe1++
		if (state == "BND") ppe1_bnd++
	} else if (idx < 16384) {
		ppe2++
		if (state == "BND") ppe2_bnd++
	} else {
		dram++
		if (state == "BND") dram_bnd++
	}
}
BEGIN { total = shown = n4 = n6 = l2b = bnd = unb = fin = 0
	ppe1 = ppe2 = dram = ppe1_bnd = ppe2_bnd = dram_bnd = 0
	zero_l2 = zero_l2_bnd = 0; have_records = 0 }
# Some kernel versions expose only the bound count in ppe/bind.
NF == 1 && $1 ~ /^[0-9]+$/ && (state_filter == "" || state_filter == "BND") {
	total += $1
	bnd += $1
	next
}
$1 ~ /^[0-9a-fA-F]+$/ && $2 ~ /^(BND|UNB|FIN|INV)$/ {
	if (state_filter != "" && $2 != state_filter) next
	total++
	bucket(hexval($1), $2)
	if ($2 == "BND") bnd++
	if ($2 == "UNB") unb++
	if ($2 == "FIN") fin++
	type = $3
	proto = ""
	if (type == "IPv4") n4++
	if (type == "IPv6") n6++
	if (type == "L2B") l2b++
	if ((type == "IPv4" || type == "IPv6") && $4 ~ /^[35]T$/) proto = $4
	if (field("eth") == "00:00:00:00:00:00->00:00:00:00:00:00" && field("etype") == "0000") {
		zero_l2++
		if ($2 == "BND") zero_l2_bnd++
	}
	have_records = 1;
	if (total <= offset) next
	if (limit > 0 && shown >= limit) next
	shown++
	status = counter_status()
	entry[shown] = sprintf("{\"index\":%s,\"state\":%s,\"type\":%s,\"proto\":%s,\"orig\":%s,\"new_flow\":%s,\"eth\":%s,\"etype\":%s,\"vlan\":%s,\"packets\":%s,\"bytes\":%s,\"counter_status\":%s,\"ib1\":%s,\"ib2\":%s,\"data\":%s,\"raw\":{\"new_flow\":%s,\"eth\":%s,\"etype\":%s,\"vlan\":%s,\"packets\":%s,\"bytes\":%s}}",
		quote($1), quote($2), quote(type), quote(proto), quote(field("orig")),
		bound_field("new"), bound_field("eth"), bound_field("etype"), bound_field("vlan"),
		(status == "reported_bound_slot" ? counter("packets") : "null"),
		(status == "reported_bound_slot" ? counter("bytes") : "null"), quote(status),
		quote(field("ib1")), quote(field("ib2")), quote(field("data")),
		quote(field("new")), quote(field("eth")), quote(field("etype")),
		quote(field("vlan")), counter("packets"), counter("bytes"))
}
END {
	if (ppe1 + ppe2 + dram > 0)
		engine_split = sprintf(",\"ppe1\":%d,\"ppe2\":%d,\"dram\":%d,\"ppe1_bound\":%d,\"ppe2_bound\":%d,\"dram_bound\":%d",
			ppe1, ppe2, dram, ppe1_bnd, ppe2_bnd, dram_bnd)
	if (have_records)
		engine_split = engine_split sprintf(",\"zero_l2\":%d,\"zero_l2_bound\":%d", zero_l2, zero_l2_bnd)
	printf "{\"available\":true,\"counter_schema\":2,\"total\":%d,\"ipv4\":%d,\"ipv6\":%d,\"l2b\":%d,\"bound\":%d,\"unbound\":%d,\"finished\":%d,\"truncated\":%s,\"returned\":%d,\"offset\":%d,\"next_offset\":%d,\"has_more\":%s,\"entries\":[",
		total, n4, n6, l2b, bnd, unb, fin, (total > shown ? "true" : "false"), shown, offset, offset+shown, (offset+shown<total ? "true" : "false")
	for (i = 1; i <= shown; i++) {
		if (i > 1) printf ","
		printf "%s", entry[i]
	}
	printf "]%s}", engine_split
}
