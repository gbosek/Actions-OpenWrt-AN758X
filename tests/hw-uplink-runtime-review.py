"""Run the actual helper under BusyBox ash with simulated devices and netifd.

Uses OpenWrt's actual functions.sh/uci.sh. No router or host network is changed.
Absolute paths are redirected to a fixture root; external device commands are
wrapped to prevent BusyBox standalone applets from bypassing the mocks.
"""
from pathlib import Path
import json
import os
import shlex
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
build = Path('/home/bosek/xg2010g-local-build/ponwrt-5615b88-clean')
busybox = Path('/home/bosek/xg2010g-local-build/review-host-tools/usr/bin/busybox')
source = (repo / 'files/usr/sbin/xg2010g-hw-uplink').read_text()
mock = r'''#!/usr/bin/python3
from pathlib import Path
import json, os, shlex, sys, time
root = Path(os.environ['WAN_TEST_ROOT'])
name = Path(sys.argv[0]).name
args = sys.argv[1:]
state_file = root / 'state.json'
state = json.loads(state_file.read_text())
def save(): state_file.write_text(json.dumps(state))
def event(text):
    with (root / 'events').open('a') as fh: fh.write(text + '\n')
if name == 'uci':
    package = args[-1]
    if state.get('load_error') == package: sys.exit(1)
    print('package ' + package)
    for section, values in state[package].items():
        print('config ' + shlex.quote(values['type']) + ' ' + shlex.quote(section))
        for key, value in values.items():
            if key == 'type': continue
            if isinstance(value, list):
                for item in value: print('list ' + shlex.quote(key) + ' ' + shlex.quote(str(item)))
            else: print('option ' + shlex.quote(key) + ' ' + shlex.quote(str(value)))
elif name == 'ethtool':
    device = args[1]
    if device not in state['roles']: sys.exit(1)
    if args[0] == '--show-priv-flags': print('hw-uplink: ' + state['roles'][device])
    else:
        event('set ' + device + ' ' + args[-1])
        if int((root / 'sys/class/net' / device / 'flags').read_text(), 0) & 1: sys.exit(1)
        if state.get('fail_set'): sys.exit(1)
        time.sleep(state.get('set_delay', 0))
        state['roles'][device] = args[-1]; save()
elif name == 'ip':
    device, action = args[3], args[4]
    event('link ' + device + ' ' + action)
    (root / 'sys/class/net' / device / 'flags').write_text('0x1' if action == 'up' else '0x0')
elif name in ('ifdown', 'ifup'):
    user = args[0]; event(name + ' ' + user)
    state['users'][user]['up'] = name == 'ifup'; state['users'][user]['pending'] = False
    device = state['owners'][user]
    (root / 'sys/class/net' / device / 'flags').write_text('0x1' if name == 'ifup' else '0x0')
    save()
elif name == 'ubus':
    user = args[1].removeprefix('network.interface.')
    print(json.dumps(state['users'].get(user, {'up': False, 'pending': False})))
elif name == 'jsonfilter':
    status = json.load(sys.stdin)
    for argument in args:
        if argument.startswith('@.'): print(str(status.get(argument[2:], False)).lower())
elif name == 'logger': event('log ' + ' '.join(args))
elif name == 'mount': sys.exit(1)
'''

def configuration(network=None, zone=None, roles=None, users=None, owners=None, **extra):
    return dict(network=network or {'wanb': {'type': 'interface', 'proto': 'dhcp', 'device': 'lan3'}}, firewall=zone or {'wan': {'type': 'zone', 'name': 'wan', 'network': ['wanb']}}, roles=roles or {'lan3': 'off', 'lan2': 'off'}, users=users or {}, owners=owners or {}, **extra)

with tempfile.TemporaryDirectory(prefix='wan1-runtime-') as directory:
    root = Path(directory)
    for path in ['bin', 'lib/config', 'sys/kernel/debug/ppe', 'sys/class/net/lan3', 'sys/class/net/lan2', 'var/run', 'etc/config']:
        (root / path).mkdir(parents=True, exist_ok=True)
    for device in ['lan3', 'lan2']:
        (root / 'sys/class/net' / device / 'flags').write_text('0x1')
    (root / 'sys/kernel/debug/ppe/config').write_text('netdev=lan3 gdm=4\nnetdev=lan2 gdm=3\n')
    for name in ['network', 'firewall']: (root / 'etc/config' / name).write_text(name)
    functions = (build / 'package/base-files/files/lib/functions.sh').read_text().replace('/lib/config/uci.sh', str(root / 'lib/config/uci.sh'))
    uci = (build / 'package/system/uci/files/lib/config/uci.sh').read_text().replace('/sbin/uci', str(root / 'bin/uci'))
    (root / 'lib/functions.sh').write_text(functions)
    (root / 'lib/config/uci.sh').write_text(uci)
    for name in ['uci', 'ethtool', 'ip', 'ifdown', 'ifup', 'ubus', 'jsonfilter', 'logger', 'mount']:
        target = root / 'bin' / name
        target.write_text(mock); target.chmod(0o755)
    helper = source
    for path in ['/lib/functions.sh', '/sys/class/net', '/sys/kernel/debug/ppe/config', '/var/run', '/etc/config']:
        helper = helper.replace(path, str(root) + path)
    wrappers = '\n'.join(f'{name}() {{ "{root}/bin/{name}" "$@"; }}' for name in ['ethtool', 'ip', 'ifdown', 'ifup', 'ubus', 'jsonfilter', 'logger', 'mount'])
    # Shell functions take precedence over standalone applets and PATH lookup.
    helper = helper.replace('log() {', wrappers + '\nlog() {', 1)
    (root / 'helper.sh').write_text(helper)
    env = dict(os.environ, PATH=str(root / 'bin') + ':/usr/bin:/bin', WAN_TEST_ROOT=str(root))
    def prepare(state):
        (root / 'state.json').write_text(json.dumps(state))
        (root / 'events').write_text('')
        for device in ['lan3', 'lan2']: (root / 'sys/class/net' / device / 'flags').write_text('0x1')
        (root / 'var/run/xg2010g-hw-uplink.failed').unlink(missing_ok=True)
    def run(state=None):
        if state is not None: prepare(state)
        result = subprocess.run([str(busybox), 'sh', str(root / 'helper.sh')], env=env, capture_output=True, text=True, timeout=20)
        if result.stderr:
            print(result.stderr)
        return result.returncode, json.loads((root / 'state.json').read_text()), (root / 'events').read_text()
    rc, state, events = run(configuration())
    assert rc == 0 and state['roles']['lan3'] == 'on', (rc, events)
    assert events.count('set lan3 on') == 1
    rc, state, events = run()
    assert rc == 0 and events.count('set lan3 on') == 1, 'repeated role toggled again'
    rc, state, events = run(configuration(load_error='network', roles={'lan3': 'on', 'lan2': 'off'}))
    assert rc != 0 and state['roles']['lan3'] == 'on' and 'set ' not in events
    rc, state, events = run(configuration(load_error='firewall', roles={'lan3': 'on', 'lan2': 'off'}))
    assert rc != 0 and state['roles']['lan3'] == 'on' and 'set ' not in events
    rc, state, events = run(configuration(zone={'guest': {'type': 'zone', 'name': 'guest', 'masq': '1', 'network': ['wanb']}}))
    assert rc == 0 and state['roles']['lan3'] == 'off', 'guest masquerade promoted'
    network = {'wanb': {'type': 'interface', 'proto': 'dhcp', 'device': 'lan3'}, 'bridge': {'type': 'device', 'name': 'br-lan', 'type_option': 'unused', 'ports': ['lan3']}}
    # Mock stores UCI section type separately from the device's option type.
    network['bridge']['type'] = 'device'
    network['bridge']['type_option'] = 'bridge'
    # Export this fixture as an option named type, retaining config device.
    adjusted = mock.replace("if key == 'type': continue", "if key == 'type': continue\n            if key == 'type_option': key = 'type'")
    (root / 'bin/uci').write_text(adjusted)
    rc, state, events = run(configuration(network=network, roles={'lan3': 'on', 'lan2': 'off'}))
    assert rc == 0 and state['roles']['lan3'] == 'off', ('bridge was promoted', events)
    network['wanb']['device'] = 'lan3.20'
    network['bridge']['ports'] = ['lan3.10']
    rc, state, events = run(configuration(network=network))
    assert rc == 0 and state['roles']['lan3'] == 'off' and 'set lan3 on' not in events, ('LAN/WAN VLAN trunk promoted', events)
    network['bridge']['ports'] = ['internal']
    network['vlan'] = {'type': 'device', 'type_option': '8021q', 'name': 'internal', 'ifname': 'lan3'}
    rc, state, events = run(configuration(network=network))
    assert rc == 0 and state['roles']['lan3'] == 'off', ('named bridge VLAN promoted', events)
    network.pop('bridge')
    runtime_bridge = root / 'sys/class/net/internal/brport'
    runtime_bridge.mkdir(parents=True)
    rc, state, events = run(configuration(network=network))
    assert rc == 0 and state['roles']['lan3'] == 'off', ('runtime bridge VLAN promoted', events)
    runtime_bridge.rmdir()
    network = {'wan6': {'type': 'interface', 'proto': 'dhcpv6', 'device': '@wanb'}, 'wanb': {'type': 'interface', 'proto': 'dhcp', 'device': 'uplink', 'hw_uplink': '1'}, 'vlan': {'type': 'device', 'type_option': '8021q', 'name': 'uplink', 'ifname': 'lan3'}, 'other': {'type': 'interface', 'proto': 'dhcp', 'device': 'lan2'}}
    zone = {'wan': {'type': 'zone', 'name': 'wan', 'network': ['wan6', 'wanb', 'other']}}
    users = {name: {'up': True, 'pending': False} for name in ['wanb', 'wan6']}
    owners = {'wanb': 'lan3', 'wan6': 'lan3'}
    rc, state, events = run(configuration(network=network, zone=zone, users=users, owners=owners))
    assert rc == 0 and state['roles'] == {'lan3': 'on', 'lan2': 'off'}, (rc, events)
    for user in ['wanb', 'wan6']:
        assert 'ifdown ' + user in events and 'ifup ' + user in events and state['users'][user]['up']
    network['wanb'].pop('hw_uplink')
    rc, state, events = run(configuration(network=network, zone=zone, roles={'lan3': 'on', 'lan2': 'off'}))
    assert rc != 0 and state['roles']['lan3'] == 'on' and 'set ' not in events
    network['other']['hw_uplink'] = '1'
    rc, state, events = run(configuration(network=network, zone=zone, roles={'lan3': 'on', 'lan2': 'off'}))
    assert rc == 0 and state['roles'] == {'lan3': 'off', 'lan2': 'on'}, (rc, events)
    assert events.index('set lan3 off') < events.index('set lan2 on'), 'new slot selected before release'
    network = {'wanb': {'type': 'interface', 'proto': 'dhcp', 'device': 'lan3', 'disabled': '1'}}
    rc, state, events = run(configuration(network=network, roles={'lan3': 'on', 'lan2': 'off'}))
    assert rc == 0 and state['roles']['lan3'] == 'off', 'disabled WAN retained its role'
    rc, state, events = run(configuration(fail_set=True, users={'wanb': {'up': True, 'pending': False}}, owners={'wanb': 'lan3'}))
    assert rc != 0 and state['roles']['lan3'] == 'off' and state['users']['wanb']['up']
    assert (root / 'sys/class/net/lan3/flags').read_text() == '0x1'
    rc, state, events = run()
    assert rc != 0 and events.count('set lan3 on') == 1, 'failed role flapped repeatedly'
    prepare(configuration(set_delay=0.15))
    processes = [subprocess.Popen([str(busybox), 'sh', str(root / 'helper.sh')], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
    for process in processes:
        out, error = process.communicate(timeout=20)
        assert process.returncode == 0, error
    assert (root / 'events').read_text().count('set lan3 on') == 1, 'concurrent events were not serialized'
print('PASS: BusyBox ash helper, idempotence, UCI failure, guest zone, early/runtime/VLAN bridges, named VLAN, IPv6 alias, preference, shared-interface restore, ambiguity, failure cooldown and concurrent flock')
