"""Run board helpers in BusyBox ash against temporary proc/sys fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
busybox = '/home/bosek/xg2010g-local-build/review-host-tools/usr/bin/busybox'
with tempfile.TemporaryDirectory(prefix='xg-steering-') as directory:
    root = Path(directory)
    for path in ['sys/class/net/eth0/queues/rx-0', 'proc/sys/net/core', 'etc/init.d', 'bin', 'sys/class/thermal/thermal_zone0', 'sys/class/ieee80211']:
        (root / path).mkdir(parents=True)
    (root / 'proc/cpuinfo').write_text(''.join('processor : %d\n' % i for i in range(4)))
    sock = root / 'proc/sys/net/core/rps_sock_flow_entries'
    mask = root / 'sys/class/net/eth0/queues/rx-0/rps_cpus'
    flows = root / 'sys/class/net/eth0/queues/rx-0/rps_flow_cnt'
    uci = root / 'bin/uci'
    uci.write_text('#!/bin/sh\ncase "$*" in *packet_steering*) echo "$TEST_MODE";; *steering_flows*) echo 128;; *) exit 1;; esac\n')
    uci.chmod(0o755)
    stock = root / 'etc/init.d/packet_steering'
    stock.write_text(f'#!/bin/sh\nprintf "2\\n" > "{mask}"\nprintf "128\\n" > "{flows}"\n')
    stock.chmod(0o755)
    source = (repo / 'files/usr/libexec/xg2010g-packet-steering').read_text().replace('. /usr/share/libubox/jshn.sh', ':')
    for path in ['/sys/class/net', '/proc/cpuinfo', '/proc/sys/net/core', '/etc/init.d/packet_steering']:
        source = source.replace(path, str(root) + path)
    script = root / 'steering.sh'
    script.write_text(source)
    for mode, expected_mask, expected_sock in [('0', '0', '0'), ('1', '2', '32768'), ('2', 'f', '32768')]:
        sock.write_text('32768\n'); mask.write_text('0\n'); flows.write_text('0\n')
        env = dict(os.environ, PATH=str(root / 'bin') + ':/usr/bin:/bin', TEST_MODE=mode)
        result = subprocess.run([busybox, 'sh', str(script), 'apply-runtime'], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert mask.read_text().strip() == expected_mask, (mode, mask.read_text())
        assert sock.read_text().strip() == expected_sock
        assert flows.read_text().strip() == ('0' if mode == '0' else '128')
    temperature = root / 'sys/class/thermal/thermal_zone0/temp'
    temp_script = root / 'tempinfo.sh'
    contents = (repo / 'files/sbin/tempinfo').read_text().replace('/sys/class/thermal', str(root / 'sys/class/thermal')).replace('/sys/class/ieee80211', str(root / 'sys/class/ieee80211'))
    assert '/usr/sbin/ponctl' not in contents
    temp_script.write_text(contents)
    for value, expected in [('69300', 'CPU: 69.3°C'), ('0', 'CPU: 0.0°C'), ('null', 'No temperature info'), ('', 'No temperature info')]:
        temperature.write_text(value + '\n')
        result = subprocess.run([busybox, 'sh', str(temp_script)], capture_output=True, text=True)
        assert result.returncode == 0 and result.stdout == expected, (value, result.stdout, result.stderr)
print('PASS: actual ash steering modes 0/1/2, all four cores, mode-1 ownership, numeric/invalid temperatures and no duplicate PON subprocess')
