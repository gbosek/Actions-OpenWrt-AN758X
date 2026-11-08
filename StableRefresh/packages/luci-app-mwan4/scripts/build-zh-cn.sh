#!/bin/sh
set -eu

src=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out=${1:-"$src/dist/zh-cn"}
po2lmo=${PO2LMO:-po2lmo}
apk=${APK:-apk}
mkdir -p "$out"
out=$(CDPATH= cd -- "$out" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

msgfmt --check -o "$work/mwan4.mo" "$src/po/zh_Hans/mwan4.po"
"$po2lmo" "$src/po/zh_Hans/mwan4.po" "$out/mwan4.zh-cn.lmo"
mkdir -p "$work/root/usr/lib/lua/luci/i18n" "$work/root/etc/uci-defaults"
cp "$out/mwan4.zh-cn.lmo" "$work/root/usr/lib/lua/luci/i18n/"
printf "%s\n" "uci set luci.languages.zh_cn='简体中文 (Simplified Chinese)'; uci commit luci" \
    > "$work/root/etc/uci-defaults/luci-i18n-mwan4-zh-cn"
find "$work/root" -type d -exec chmod 755 {} +
find "$work/root" -type f -exec chmod 644 {} +
"$apk" mkpkg --files "$work/root" \
    --info 'name:luci-i18n-mwan4-zh-cn' \
    --info 'version:1.0.0-r10' \
    --info 'arch:noarch' \
    --info 'license:AGPL-3.0-or-later' \
    --info 'description:简体中文翻译 - LuCI MWAN4 多线路管理' \
    --info 'depends:luci-app-mwan4' \
    --output "$out/luci-i18n-mwan4-zh-cn-1.0.0-r10.apk"
printf 'Language artifacts: %s\n' "$out"
