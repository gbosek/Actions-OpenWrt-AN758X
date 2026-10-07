#!/usr/bin/env python3
"""Check the same XG2010G package contract at every build stage."""
import argparse
from pathlib import Path
import re


def package_names(stage, text):
    if stage == 'config':
        return set(re.findall(r'^CONFIG_PACKAGE_([A-Za-z0-9+_.-]+)=y\s*$', text, re.M))
    if stage == 'index':
        return set(re.findall(r'^Package: ([A-Za-z0-9+_.-]+)$', text, re.M))
    if stage == 'installed':
        return set(re.findall(r'^P:([A-Za-z0-9+_.-]+)$', text, re.M))
    return set(re.findall(r'^([A-Za-z0-9+_.-]+) - ', text, re.M))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['config', 'index', 'manifest', 'installed'])
    parser.add_argument('path', type=Path)
    parser.add_argument('--requirements', type=Path, default=Path(__file__).resolve().parents[1] / 'configs/xg2010g-required-packages.txt')
    args = parser.parse_args()
    required = [line.strip() for line in args.requirements.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if len(required) != len(set(required)) or any(not re.fullmatch(r'[A-Za-z0-9+_.-]+', name) for name in required):
        parser.error('invalid or duplicate required package names')
    names = package_names(args.stage, args.path.read_text())
    forbidden_names = names
    missing = sorted(set(required) - names)
    forbidden_set = set()
    if args.stage != 'index':
        forbidden_set.update({
            'luci-app-pon',
            'luci-app-iptv',
            'vnstat',
            'luci-app-natmode',
            'luci-app-vnstat2',
            'luci-i18n-vnstat2-zh-cn',
            'vnstat2',
            'vnstati2',
            'luci-app-statistics',
            'luci-i18n-statistics-zh-cn',
            'collectd',
            'collectd-mod-cpu',
            'collectd-mod-memory',
            'collectd-mod-interface',
            'collectd-mod-load',
            'collectd-mod-rrdtool',
            'collectd-mod-thermal',
            'collectd-mod-cpufreq',
            'rrdtool1'
        })
    if args.stage == 'config':
        all_configured = set(re.findall(r'^CONFIG_PACKAGE_([A-Za-z0-9+_.-]+)=[ym]\s*$', args.path.read_text(), re.M))
        forbidden_names = all_configured
        forbidden_set.update({'luci-proto-wireguard', 'wireguard-tools', 'kmod-wireguard'})
    elif args.stage != 'index':
        forbidden_set.update({'luci-proto-wireguard', 'wireguard-tools', 'kmod-wireguard'})
    forbidden = sorted(forbidden_names & forbidden_set)
    if missing or forbidden:
        if missing:
            print('::error::XG2010G packages missing at ' + args.stage + ': ' + ', '.join(missing))
        if forbidden:
            print('::error::Packages forbidden in this XG2010G image: ' + ', '.join(forbidden))
        return 1
    print(f'PASS: XG2010G {args.stage}, {len(required)} required packages')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
