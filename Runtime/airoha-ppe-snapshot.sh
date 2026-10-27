#!/bin/sh
# Sourced by either Airoha rpcd backend. A dashboard listing is bounded;
# a user-requested export parses every record, behind a separate deadline.
. /usr/libexec/airoha-deadline.sh

_ppe_boot_id() {
    local value
    value=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
    case "$value" in ''|*[!0-9a-f-]*) value=unknown ;; esac
    printf '%s' "$value"
}

_ppe_snapshot_json() {
    local limit="$1" snapshot parsed captured_at started ended ms deadline=2
    local stats=null reason=driver_capability_unreported cap cached now cache_at boot_id
    local cache=/tmp/xg2010g-ppe-v4.cache
    if [ "$limit" = 1024 ] && [ -s "$cache" ]; then
        now=$(date +%s)
        IFS= read -r cache_at < "$cache"
        case "$cache_at" in ''|*[!0-9]*) cache_at=0 ;; esac
        if [ "$now" -ge "$cache_at" ] && [ "$((now-cache_at))" -lt 2 ]; then
            cached=$(sed -n '2,$p' "$cache")
            case "$cached" in \{*\})
                command -v _airoha_ppe_publish_counts >/dev/null && _airoha_ppe_publish_counts "$cached"
                printf '%s\n' "$cached"; return 0 ;;
            esac
        fi
    fi
    [ "$limit" = 0 ] && deadline=5
    snapshot=$(mktemp /tmp/xg2010g-ppe.XXXXXX) || {
        echo '{"available":false,"error":"snapshot_create_failed","entries":[]}'; return;
    }
    captured_at=$(date +%s)
    started=$(awk '{print $1}' /proc/uptime)
    boot_id=$(_ppe_boot_id)
    if ! _run_with_deadline "$deadline" ppe cp /sys/kernel/debug/ppe/entries "$snapshot"; then
        rm -f "$snapshot"
        echo '{"available":false,"error":"ppe_read_failed_or_timeout","entries":[]}'; return;
    fi
    cap=$(awk '$1=="flow_stats_cap:" {print $2;exit}' /sys/kernel/debug/ppe/config 2>/dev/null)
    if ! parsed=$(awk -v limit="$limit" -v stats_cap="$cap" -f /usr/libexec/airoha-ppe.awk "$snapshot"); then
        rm -f "$snapshot"
        echo '{"available":false,"error":"ppe_parse_failed","entries":[]}'; return;
    fi
    rm -f "$snapshot"
    case "$cap" in
        1) stats=true; reason=driver_capability_enabled ;;
        0) stats=false; reason=driver_capability_disabled ;;
    esac
    ended=$(awk '{print $1}' /proc/uptime)
    ms=$(awk -v a="$started" -v b="$ended" 'BEGIN {printf "%.0f",(b-a)*1000}')
    parsed="${parsed%\}},\"captured_at\":$captured_at,\"boot_id\":\"$boot_id\",\"captured_uptime\":$started,\"read_ms\":$ms,\"list_limit\":$limit,\"snapshot_atomic\":false,\"flow_stats_available\":$stats,\"flow_stats_reason\":\"$reason\"}"
    if [ "$limit" = 1024 ]; then
        snapshot=$(mktemp /tmp/xg2010g-ppe.cache.XXXXXX)
        if [ -n "$snapshot" ]; then
            { date +%s; printf '%s\n' "$parsed"; } > "$snapshot"
            mv -f "$snapshot" "$cache" || rm -f "$snapshot"
        fi
    fi
    command -v _airoha_ppe_publish_counts >/dev/null && _airoha_ppe_publish_counts "$parsed"
    printf '%s\n' "$parsed"
}
get_ppe_entries() { _ppe_snapshot_json 1024; }
# Each ubus response stays bounded. Every page comes from one captured raw
# snapshot, so changing live entries cannot create duplicates between pages.
_ppe_export_page() {
    local token="$1" offset="${2:-0}" dir stamp cap stats=null reason=driver_capability_unreported
    local parsed now ms started ended more boot_id capture_uptime
    umask 077
    case "$offset" in ''|*[!0-9]*) echo '{"available":false,"error":"invalid_offset","entries":[]}'; return ;; esac
    [ "$offset" -le 1048576 ] 2>/dev/null || { echo '{"available":false,"error":"invalid_offset","entries":[]}'; return; }
    if [ -z "$token" ]; then
        [ "$offset" = 0 ] || { echo '{"available":false,"error":"snapshot_required","entries":[]}'; return; }
        # Clean abandoned exports only when another export is requested.
        for dir in /tmp/xg2010g-ppe-export.??????; do
            [ -d "$dir" ] && [ ! -L "$dir" ] && [ -r "$dir/meta" ] || continue
            read -r stamp cap boot_id capture_uptime < "$dir/meta"
            now=$(date +%s)
            case "$stamp" in ''|*[!0-9]*) continue ;; esac
            if [ "$now" -gt "$((stamp+300))" ]; then
                rm -f "$dir/entries" "$dir/meta"; rmdir "$dir" 2>/dev/null
            fi
        done
        dir=$(mktemp -d /tmp/xg2010g-ppe-export.XXXXXX) || {
            echo '{"available":false,"error":"snapshot_create_failed","entries":[]}'; return;
        }
        token=${dir##*.}; stamp=$(date +%s)
        boot_id=$(_ppe_boot_id); capture_uptime=$(awk '{print $1}' /proc/uptime)
        if ! _run_with_deadline 5 ppe cp /sys/kernel/debug/ppe/entries "$dir/entries"; then
            rm -f "$dir/entries"; rmdir "$dir"
            echo '{"available":false,"error":"ppe_read_failed_or_timeout","entries":[]}'; return;
        fi
        cap=$(awk '$1=="flow_stats_cap:" {print $2;exit}' /sys/kernel/debug/ppe/config 2>/dev/null)
        printf '%s %s %s %s\n' "$stamp" "${cap:-unknown}" "$boot_id" "$capture_uptime" > "$dir/meta"
    else
        case "$token" in *[!a-zA-Z0-9]*|?????|???????* ) echo '{"available":false,"error":"invalid_snapshot","entries":[]}'; return ;; esac
        [ "${#token}" = 6 ] || { echo '{"available":false,"error":"invalid_snapshot","entries":[]}'; return; }
        dir=/tmp/xg2010g-ppe-export.$token
        if [ -L "$dir" ] || [ ! -r "$dir/meta" ] || [ ! -r "$dir/entries" ]; then
            echo '{"available":false,"error":"snapshot_expired","entries":[]}'; return;
        fi
        read -r stamp cap boot_id capture_uptime < "$dir/meta"
        now=$(date +%s)
        if [ "$now" -lt "$stamp" ] || [ "$now" -gt "$((stamp+300))" ]; then
            rm -f "$dir/entries" "$dir/meta"; rmdir "$dir" 2>/dev/null
            echo '{"available":false,"error":"snapshot_expired","entries":[]}'; return;
        fi
    fi
    case "$boot_id" in ''|*[!0-9a-f-]*) boot_id=unknown ;; esac
    case "$capture_uptime" in ''|*[!0-9.]*) capture_uptime=null ;; esac
    case "$cap" in 1) stats=true; reason=driver_capability_enabled ;; 0) stats=false; reason=driver_capability_disabled ;; esac
    started=$(awk '{print $1}' /proc/uptime)
    if ! parsed=$(awk -v limit=128 -v offset="$offset" -v stats_cap="$cap" -f /usr/libexec/airoha-ppe.awk "$dir/entries"); then
        echo '{"available":false,"error":"ppe_parse_failed","entries":[]}'; return;
    fi
    ended=$(awk '{print $1}' /proc/uptime)
    ms=$(awk -v a="$started" -v b="$ended" 'BEGIN {printf "%.0f",(b-a)*1000}')
    printf '%s,"export_id":"%s","captured_at":%s,"boot_id":"%s","captured_uptime":%s,"read_ms":%s,"list_limit":128,"snapshot_atomic":false,"export_snapshot_stable":true,"flow_stats_available":%s,"flow_stats_reason":"%s"}\n' "${parsed%\}}" "$token" "$stamp" "$boot_id" "$capture_uptime" "$ms" "$stats" "$reason"
    # The last page can safely release the snapshot; an abandoned one expires.
    more=$(printf '%s' "$parsed" | jsonfilter -e '@.has_more' 2>/dev/null)
    if [ "$more" = false ]; then rm -f "$dir/entries" "$dir/meta"; rmdir "$dir" 2>/dev/null; fi
}
get_ppe_export() {
    local token offset
    token=$(printf '%s' "$1" | jsonfilter -e '@.snapshot' 2>/dev/null)
    offset=$(printf '%s' "$1" | jsonfilter -e '@.offset' 2>/dev/null)
    _ppe_export_page "$token" "${offset:-0}"
}
