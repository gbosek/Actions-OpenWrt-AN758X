#!/bin/sh
# XG2010G runtime MWAN4 table mapping. IPv6 remains source-prefix routed.
[ "$(cat /tmp/sysinfo/board_name 2>/dev/null)" = gemtek,xg2010g ] || exit 0
PLAN=0
[ "$1" = "--plan" ] && PLAN=1
ROUTES_ONLY=0
[ "$1" = "--routes-only" ] && ROUTES_ONLY=1
. /lib/functions.sh
# A descriptor lock is released automatically after a crash. It also serializes
# native stop cleanup with an interface event already in flight.
state=/var/run/mwan4-rule-guard.dns-owned
if [ "$PLAN" = 0 ]; then
    exec 9>/var/run/mwan4-rule-guard.flock
    flock -w 5 9 || { logger -t mwan4-rule-guard 'route lock timed out'; exit 1; }
fi
cleanup_owned_dns() {
    [ -r "$state" ] || return 0
    while IFS='|' read -r fam pref spec; do
        case "$fam:$pref:$spec" in 4:9[0-9][0-9][0-9]:to\ *\ lookup\ *|6:9[0-9][0-9][0-9]:to\ *\ lookup\ *)
            if [ "$PLAN" = 1 ]; then printf 'DEL ip -%s rule del pref %s %s\n' "$fam" "$pref" "$spec"
            else ip "-$fam" rule del pref "$pref" $spec 2>/dev/null
            fi ;;
        esac
    done < "$state"
    [ "$PLAN" = 1 ] || rm -f "$state"
    return 0
}
# Native MWAN4 owns its fallback rules. Never resurrect a stopped service.
if [ "$1" = --cleanup ] || [ ! -d /var/run/mwan4 ] || [ -e /var/run/mwan4-rule-guard.stopped ] ||
   { [ "${MWAN4_STARTUP:-}" != init ] && ! /etc/init.d/mwan4 running; }; then
    cleanup_owned_dns
    exit 0
fi
config_load mwan4
config_get mask globals mmx_mask 0x3f00
case "$mask" in 0x[0-9a-fA-F]*|[0-9]*) ;; *) exit 1 ;; esac
mask=$(printf '0x%x' "$((mask))")
MAP=''
ID=0
map_iface() {
    local name="$1" enabled family dev up fam data
    ID=$((ID+1))
    config_get enabled "$name" enabled 0
    [ "$enabled" = 1 ] || return
    config_get family "$name" family ipv4
    data=$(ubus call "network.interface.$name" status 2>/dev/null)
    dev=$(printf '%s' "$data" | jsonfilter -e '@.l3_device')
    up=$(printf '%s' "$data" | jsonfilter -e '@.up')
    [ "$up" = true ] || return
    case "$dev" in ''|*[!a-zA-Z0-9_.:-]*) return ;; esac
    case "$family" in ipv4) family=4 ;; ipv6) family=6 ;; 'ipv4 ipv6'|'ipv6 ipv4'|any) family='4 6' ;; *) return ;; esac
    for fam in $family; do
        MAP="${MAP}${fam} ${name} ${ID} ${dev}
"
    done
}
config_foreach map_iface interface
mark_for_id() {
    local value="$1" bits=$((mask)) bit=0 result=0
    while [ "$bits" -gt 0 ]; do
        if [ $((bits & 1)) = 1 ]; then
            result=$((result | ((value & 1) << bit)))
            value=$((value >> 1))
        fi
        bits=$((bits >> 1)); bit=$((bit+1))
    done
    printf '0x%x' "$result"
}
has_exact() {
    ip "-$1" rule show | awk -v wanted="$2: from all $3" '
        { gsub(/[ \t]+/," "); sub(/ +$/ ,""); if($0==wanted) found=1 }
        END{exit !found}'
}
add_exact() {
    local fam="$1" pref="$2" spec="$3"
    [ ! -e /var/run/mwan4-rule-guard.stopped ] || return 1
    has_exact "$fam" "$pref" "$spec" && return 0
    if [ "$PLAN" = 1 ]; then printf 'ADD ip -%s rule add pref %s %s\n' "$fam" "$pref" "$spec"
    else ip "-$fam" rule add pref "$pref" $spec
    fi
}
del_exact() {
    local fam="$1" pref="$2" spec="$3" n
    has_exact "$fam" "$pref" "$spec" || return 0
    if [ "$PLAN" = 1 ]; then printf 'DEL ip -%s rule del pref %s %s\n' "$fam" "$pref" "$spec"; return; fi
    for n in 1 2 3 4 5 6 7 8; do
        has_exact "$fam" "$pref" "$spec" || return 0
        ip "-$fam" rule del pref "$pref" $spec || return 1
    done
}
find_id() {
    printf '%s' "$MAP" | awk -v f="$1" -v n="$2" '$1==f && $2==n {print $3;exit}'
}
printf '%s' "$MAP" | while read -r fam name tid dev; do
    [ -n "$tid" ] || continue
    [ -n "$(ip "-$fam" route show table "$tid")" ] || continue
    mark=$(mark_for_id "$tid")
    add_exact "$fam" $((tid+1000)) "iif $dev lookup $tid"
    add_exact "$fam" $((tid+2000)) "fwmark $mark/$mask lookup $tid"
    add_exact "$fam" $((tid+3000)) "fwmark $mark/$mask unreachable"
    if [ "$PLAN" = 0 ]; then
        has_exact "$fam" $((tid+1000)) "iif $dev lookup $tid" &&
        has_exact "$fam" $((tid+2000)) "fwmark $mark/$mask lookup $tid" &&
        has_exact "$fam" $((tid+3000)) "fwmark $mark/$mask unreachable" || continue
    fi
    # Remove only the exact legacy v6 rules after the native replacement exists.
    if [ "$fam" = 6 ]; then
        base=${name%_6}; old=$(find_id 4 "$base")
        if [ -n "$old" ] && [ "$old" != "$tid" ] && [ -z "$(ip -6 route show table "$old")" ] &&
           [ -n "$(ip -6 route show table "$tid")" ]; then
            oldmark=$(mark_for_id "$old")
            del_exact 6 $((old+1000)) "iif $dev lookup $old"
            del_exact 6 $((old+2000)) "fwmark $oldmark/$mask lookup $old"
            del_exact 6 $((old+3000)) "fwmark $oldmark/$mask unreachable"
        fi
    fi
done
tmp="${state}.$$"
[ "$PLAN" = 1 ] || : > "$tmp"
if [ -r /tmp/resolv.conf.d/resolv.conf.auto ]; then
    awk '/^# Interface /{n=$3} /^nameserver /{print ($2 ~ /:/ ? 6:4),n,$2}' /tmp/resolv.conf.d/resolv.conf.auto |
    {
        p4=9000; p6=9100
        while read -r fam name dns; do
            case "$dns" in ''|*[!0-9a-fA-F:.]*) continue ;; esac
            tid=$(find_id "$fam" "$name")
            base=${name%_6}
            if [ -z "$tid" ]; then
                if [ "$fam" = 6 ]; then tid=$(find_id 6 "${base}_6"); else tid=$(find_id 4 "$base"); fi
            fi
            [ -n "$tid" ] || continue
            if [ "$fam" = 6 ]; then p6=$((p6+1)); pref=$p6; else p4=$((p4+1)); pref=$p4; fi
            spec="to $dns lookup $tid"
            add_exact "$fam" "$pref" "$spec" || continue
            [ "$PLAN" = 1 ] || printf '%s|%s|%s\n' "$fam" "$pref" "$spec" >> "$tmp"
            old=$(find_id 4 "$base")
            if [ "$fam" = 6 ] && [ -n "$old" ] && [ "$old" != "$tid" ] && [ -z "$(ip -6 route show table "$old")" ]; then
                del_exact 6 "$pref" "to $dns lookup $old"
            fi
        done
    }
fi
if [ "$PLAN" = 0 ]; then
    if [ -r "$state" ]; then
        while IFS='|' read -r fam pref spec; do
            case "$fam:$pref:$spec" in 4:9[0-9][0-9][0-9]:to\ *\ lookup\ *|6:9[0-9][0-9][0-9]:to\ *\ lookup\ *) ;; *) continue ;; esac
            grep -Fqx "$fam|$pref|$spec" "$tmp" || del_exact "$fam" "$pref" "$spec"
        done < "$state"
    fi
    mv -f "$tmp" "$state"
    # A native stop may arrive while this event snapshot is being processed.
    [ ! -e /var/run/mwan4-rule-guard.stopped ] || cleanup_owned_dns
fi
[ "$PLAN" = 1 ] && exit 0
[ "$ROUTES_ONLY" = 1 ] && exit 0
exit 0
