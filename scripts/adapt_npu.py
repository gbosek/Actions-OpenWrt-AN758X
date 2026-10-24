#!/usr/bin/env python3
"""Adapt CPU controls in either NPU view to the shared kernel policy owner."""
import re
from pathlib import Path


def replace_function(text, name, body):
    pattern = r'^' + re.escape(name) + r'\(\) \{.*?\n\}'
    text, count = re.subn(pattern, lambda _: body, text, flags=re.M | re.S)
    if count != 1:
        raise ValueError(f'Cannot uniquely adapt {name}')
    return text


def adapt(app, variant):
    rpc = app / 'root/usr/libexec/rpcd/luci.airoha_npu'
    text = rpc.read_text()
    text = replace_function(text, 'set_governor', '''set_governor() {
	local governor
	governor=$(printf '%s' "$1" | jsonfilter -e '@.governor' 2>/dev/null)
	/usr/libexec/xg2010g-cpu-policy set-governor "$governor"
}''')
    text = replace_function(text, 'set_max_freq', '''set_max_freq() {
	local freq
	freq=$(printf '%s' "$1" | jsonfilter -e '@.freq' 2>/dev/null)
	/usr/libexec/xg2010g-cpu-policy set-max "$freq"
}''')
    if variant == 'naoki':
        text = replace_function(text, '_cpu_frequencies', '''_cpu_frequencies() {
	/usr/libexec/xg2010g-cpu-policy frequencies
}''')
        text = replace_function(text, 'set_cpu_settings', '''set_cpu_settings() {
	local governor freq result
	governor=$(printf '%s' "$1" | jsonfilter -e '@.governor' 2>/dev/null)
	freq=$(printf '%s' "$1" | jsonfilter -e '@.freq' 2>/dev/null)
	if [ -z "$governor" ] && [ -z "$freq" ]; then
		echo '{"error":"Missing CPU settings"}'; return 1
	fi
	if [ -n "$freq" ]; then
		result=$(/usr/libexec/xg2010g-cpu-policy set-max "$freq") || { echo "$result"; return 1; }
	fi
	if [ -n "$governor" ]; then
		result=$(/usr/libexec/xg2010g-cpu-policy set-governor "$governor") || { echo "$result"; return 1; }
	fi
	echo '{"result":"ok","persisted":true}'
}''')
        init = app / 'root/etc/init.d/airoha-npu'
        init.write_text('''#!/bin/sh /etc/rc.common
# Manual compatibility alias. The standard cpufreq service is the boot owner.
# No START entry: this helper does not apply a second boot policy.
start() { /usr/libexec/xg2010g-cpu-policy apply; }
reload() { start; }
''')
        config = app / 'root/etc/config/airoha_npu'
        config.write_text(config.read_text().replace("option max_freq '1200000'", "option max_freq '1400000'"))
    else:
        old = 'cpu_avail_freqs=$(cat "$cpufreq_path/scaling_available_frequencies" 2>/dev/null || echo "")'
        if text.count(old) != 1:
            raise ValueError('Luanmuc CPU frequency enumeration changed')
        text = text.replace(old, 'cpu_avail_freqs=$(/usr/libexec/xg2010g-cpu-policy frequencies | tr "\\n" " ")')
        text = replace_function(text, 'set_overclock', '''set_overclock() {
	local target_mhz
	target_mhz=$(printf '%s' "$1" | jsonfilter -e '@.freq_mhz' 2>/dev/null)
	case "$target_mhz" in ''|*[!0-9]*) echo '{"error":"Invalid frequency"}'; return 1;; esac
	[ "$target_mhz" -ge 500 ] && [ "$target_mhz" -le 1400 ] || {
		echo '{"error":"Frequency must be 500–1400 MHz"}'; return 1
	}
	/usr/libexec/xg2010g-cpu-policy set-max "$((target_mhz * 1000))"
}''')
        js = app / 'htdocs/luci-static/resources/view/airoha_npu/status.js'
        s = js.read_text().replace("'max':'1600'", "'max':'1400'").replace('f>1600', 'f>1400').replace('Frequency must be 500-1600 MHz', 'Frequency must be 500-1400 MHz')
        s = s.replace("if(f>1400&&!confirm(_('Frequencies above 1400 MHz may be unstable. Continue?'))) return;", '')
        s = s.replace("_('CPU set to ')+r.actual_mhz+' MHz'", "_('Maximum frequency ceiling applied')")
        s = s.replace('Direct PLL programming. Governor locked to performance. Stock max: 1200 MHz. Tested stable up to 1500 MHz.', 'CPU frequency is managed by the kernel; governor is preserved.')
        js.write_text(s)
        po = app / 'po/zh_Hans/airoha-npu.po'
        po.write_text(po.read_text()+'''\nmsgid "Maximum frequency ceiling applied"
msgstr "最高频率上限已应用"

msgid "CPU frequency is managed by the kernel; governor is preserved."
msgstr "CPU 频率由内核管理，保留当前调速器设置。"

msgid "Frequency must be 500-1400 MHz"
msgstr "频率必须在 500–1400 MHz 范围内"
''')
    # Keep NPU status fields intact while exposing the compatibility capability.
    text = text.replace('get_status() {', 'upstream_get_status() {', 1)
    text = text.replace('case "$1" in\n\tlist)', '''get_status() {
	local status cap backend
	status=$(upstream_get_status)
	cap=$(/usr/libexec/xg2010g-cpu-policy cap)
	backend=$(/usr/libexec/xg2010g-cpu-policy backend)
	case "$status" in
		*'}') printf '%s,"boost_capable":%s,"boost_backend":"%s"}\\n' "${status%\\}}" "$cap" "$backend";;
		*) printf '%s\\n' "$status";;
	esac
}

case "$1" in
	list)''', 1)
    if 'boost_backend' not in text or '/usr/libexec/xg2010g-cpu-policy set-max' not in text:
        raise ValueError('CPU adapter did not apply')
    rpc.write_text(text)
    from observability import adapt_observability
    adapt_observability(app, variant)
    make = app / 'Makefile'
    s = make.read_text()
    revision = 7 if variant == 'naoki' else 2
    s, n = re.subn(r'^PKG_RELEASE:=(\d+)$', lambda m: 'PKG_RELEASE:='+str(int(m[1])*100+revision), s, flags=re.M)
    if n != 1: raise ValueError('Cannot assign a distinct local package revision')
    make.write_text(s)
