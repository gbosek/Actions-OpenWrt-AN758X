#!/usr/bin/env python3
"""Run shipped guard/watcher code against queue files and real flock processes."""
from pathlib import Path
import os, subprocess, tempfile, time

package = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    net = root / 'net/pon0/queues/rx-0'
    net.mkdir(parents=True)
    board = root / 'board'
    board.write_text('gemtek,xg2010g')
    sock = root / 'sock'
    log = root / 'log'
    changes = root / 'changes'
    binpath = root / 'bin'
    binpath.mkdir()
    def executable(name, text):
        path = binpath / name
        path.write_text(text)
        path.chmod(0o755)
        return path
    executable('uci', '#!/bin/sh\nprintf "%s" "${STEERING:-2}"\n')
    executable('logger', '#!/bin/sh\nprintf "%s\\n" "$*" >> "' + str(log) + '"\n')
    tune = executable('tune', '#!/bin/sh\nprintf f > "' + str(net / 'rps_cpus') + '"\nprintf 1024 > "' + str(net / 'rps_flow_cnt') + '"\nprintf 4096 > "' + str(sock) + '"\necho tuned >> "' + str(changes) + '"\n')
    text = (package / 'files/rps-guard.sh').read_text().replace('/tmp/sysinfo/board_name', str(board)).replace('/sys/class/net', str(root / 'net')).replace('/proc/sys/net/core/rps_sock_flow_entries', str(sock)).replace('/usr/bin/rps-tune.sh', str(tune))
    guard = executable('guard', text)
    env = dict(os.environ, PATH=str(binpath) + ':' + os.environ['PATH'])
    for path, value in [(net / 'rps_cpus', 'f'), (net / 'rps_flow_cnt', '1024'), (sock, '4096')]:
        path.write_text(value)  # No trailing newline: read's exit status must not erase data.
    subprocess.run(['sh', str(guard)], env=env, check=True)
    assert not log.exists() and not changes.exists(), 'Healthy values were misreported as drift'
    (net / 'rps_cpus').write_text('0')
    subprocess.run(['sh', str(guard)], env=env, check=True)
    assert changes.read_text().splitlines() == ['tuned']
    subprocess.run(['sh', str(guard)], env=env, check=True)
    assert changes.read_text().splitlines() == ['tuned'], 'Unchanged queues were rewritten again'
    (net / 'rps_cpus').write_text('0')
    subprocess.run(['sh', str(guard)], env=dict(env, STEERING='0'), check=True)
    assert (net / 'rps_cpus').read_text() == '0', 'User off switch was ignored'
    board.write_text('another,board')
    subprocess.run(['sh', str(guard)], env=env, check=True)
    assert changes.read_text().splitlines() == ['tuned']

    ticks = root / 'ticks'
    tick = executable('tick', '#!/bin/sh\necho "$PPID" >> "' + str(ticks) + '"\n')
    watcher = executable('watcher', (package / 'files/rps-watch.sh').read_text().replace('/var/run/xg2010g-rps-watch.lock', str(root / 'watch.lock')).replace('/usr/bin/rps-guard.sh', str(tick)).replace('sleep 5', 'sleep 0.05'))
    first = subprocess.Popen(['sh', str(watcher)], env=env)
    try:
        deadline = time.monotonic() + 2
        while not ticks.exists() and time.monotonic() < deadline: time.sleep(0.01)
        assert ticks.exists(), 'Watcher did not start'
        second = subprocess.run(['sh', str(watcher)], env=env, timeout=1)
        assert second.returncode == 0 and set(ticks.read_text().splitlines()) == {str(first.pid)}, 'Duplicate watcher acquired the lock'
    finally:
        first.terminate()
        first.wait(timeout=1)
    time.sleep(0.1)
    third = subprocess.Popen(['sh', str(watcher)], env=env)
    try:
        deadline = time.monotonic() + 2
        while str(third.pid) not in ticks.read_text().splitlines() and time.monotonic() < deadline: time.sleep(0.01)
        assert str(third.pid) in ticks.read_text().splitlines(), 'Lock did not release on restart'
    finally:
        third.terminate()
        third.wait(timeout=1)
print('PASS: no false drift without newline, actual drift repaired once, off switch/board respected, duplicate watcher blocked and restart succeeds')
