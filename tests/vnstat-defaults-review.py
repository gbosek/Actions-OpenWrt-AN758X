"""Exercise first-boot traffic defaults in ash without touching a router."""
from pathlib import Path
import os
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
busybox = '/home/bosek/xg2010g-local-build/review-host-tools/usr/bin/busybox'
source = (repo / 'files/etc/uci-defaults/99-xg2010g-vnstat').read_text()
with tempfile.TemporaryDirectory(prefix='xg-vnstat-') as directory:
    root = Path(directory)
    for name in ['etc/init.d', 'tmp/sysinfo', 'sys/kernel/debug/ppe', 'sys/class/net']:
        (root / name).mkdir(parents=True)
    for dev, kind in [('pon0', '1'), ('lan3', '1'), ('lan2', '1'), ('omci0', '65535')]:
        (root / 'sys/class/net' / dev).mkdir()
        (root / 'sys/class/net' / dev / 'type').write_text(kind + '\n')
    service = root / 'etc/init.d/vnstat'
    service.write_text('#!/bin/sh\nprintf "service %s\\n" "$*" >> "$TEST_LOG"\n')
    service.chmod(0o755)
    (root / 'sys/kernel/debug/ppe/config').write_text(
        'netdev=pon0 role=wan hw_wan_slot=0\n'
        'netdev=lan3 role=lan hw_wan_slot=-1\n'
        'netdev=lan3 role=wan hw_wan_slot=1\n'
        'netdev=lan2 role=lan hw_wan_slot=-1\n'
        'netdev=omci0 role=wan hw_wan_slot=-1\n'
        'netdev=bad/name role=wan hw_wan_slot=-1\n')
    prelude = '''uci() {
        [ "$1" != -q ] || shift
        case "$1" in
            get)
                case "$2" in
                    'vnstat.@vnstat[0]') return 0;;
                    'vnstat.@vnstat[0].interface') [ "$PRESET_INTERFACES" = 1 ];;
                    *) return 1;;
                esac;;
            add_list|commit) printf 'uci %s\\n' "$*" >> "$TEST_LOG";;
            *) return 1;;
        esac
    }
'''
    for path in ['/etc', '/tmp/sysinfo', '/sys/kernel/debug/ppe', '/sys/class/net']:
        source = source.replace(path, str(root) + path)
    script = root / 'defaults.sh'
    script.write_text(prelude + source)
    config = root / 'etc/vnstat.conf'
    board = root / 'tmp/sysinfo/board_name'
    log = root / 'actions.log'
    for case, config_text, preset in [
        ('defaults', '#DatabaseDir "/var/lib/vnstat"\n', '0'),
        ('custom', 'DatabaseDir "/mnt/traffic"\nSaveInterval 120\nMaxBandwidth 10000\n', '1'),
        ('other-board', '#DatabaseDir "/var/lib/vnstat"\n', '0'),
        ('no-debugfs', '#DatabaseDir "/var/lib/vnstat"\n', '0'),
    ]:
        config.write_text(config_text)
        log.write_text('')
        board.write_text('other,router\n' if case == 'other-board' else 'gemtek,xg2010g\n')
        if case == 'no-debugfs':
            (root / 'sys/kernel/debug/ppe/config').unlink()
        result = subprocess.run([busybox, 'sh', str(script)], capture_output=True, text=True,
            env=dict(os.environ, TEST_LOG=str(log), PRESET_INTERFACES=preset))
        assert result.returncode == 0, (case, result.stderr)
        actions = log.read_text()
        if case in ['custom', 'other-board']:
            assert config.read_text() == config_text, case
            assert 'add_list' not in actions, actions
        else:
            for line in [f'DatabaseDir "{root}/etc/vnstat2"', 'SaveInterval 60',
                         'OfflineSaveInterval 60', 'SaveOnStatusChange 0',
                         'BandwidthDetection 0', 'MaxBandwidth 0']:
                assert line in config.read_text(), (case, line)
        if case == 'defaults':
            for dev in ['pon0', 'lan3', 'lan2']:
                assert actions.count('add_list vnstat.@vnstat[0].interface=' + dev + '\n') == 1, actions
            assert 'omci0' not in actions and 'bad/name' not in actions and 'br-lan' not in actions
        if case == 'other-board':
            assert actions == ''
        else:
            assert 'service enable\nservice restart\n' in actions, actions
        if case == 'no-debugfs':
            assert 'add_list' not in actions, actions
assert (repo / 'files/lib/upgrade/keep.d/xg2010g-vnstat').read_text() == '/etc/vnstat2/\n'
print('PASS: vnStat physical MIB device discovery, Ethernet filtering, deduplication, hourly persistence, custom-config preservation and board/debugfs fallbacks')
