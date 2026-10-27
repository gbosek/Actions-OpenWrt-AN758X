#!/usr/bin/env python3
"""Exercise actual patched MWAN4 lifecycle and UI functions in isolated stubs."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
root = args.source.resolve()
repo = Path(__file__).resolve().parents[2]
backend = root / 'package/custom/mwan4'
frontend = root / 'package/custom/luci-app-mwan4'


def function(text, name):
    start = text.index('function ' + name + '(')
    brace = text.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


with tempfile.TemporaryDirectory(prefix='mwan4-off-') as directory:
    temp = Path(directory)
    run = temp / 'run'
    run.mkdir()
    log = temp / 'actions'
    preset, guard = temp / 'preset', temp / 'guard'
    for path, label in [(preset, 'preset'), (guard, 'guard')]:
        path.write_text('#!/bin/sh\necho "' + label + ' $*" >> "$TEST_LOG"\n')
        path.chmod(0o755)
    init = (backend / 'files/etc/init.d/mwan4').read_text()
    init = init.replace('. "${IPKG_INSTROOT}/lib/functions.sh"', ':')
    init = init.replace('/var/run', str(run)).replace('/usr/libexec/xg2010g-mwan4-preset', str(preset))
    init = init.replace('/usr/bin/mwan4-rule-guard.sh', str(guard))
    stubs = '''
procd_running() { [ "$TEST_RUNNING" = 1 ]; }
enabled() { [ "$TEST_ENABLED" = 1 ]; }
start() { echo start >> "$TEST_LOG"; }
stop() { echo stop >> "$TEST_LOG"; }
config_load() { echo config >> "$TEST_LOG"; }
config_foreach() { :; }
procd_open_instance() { :; }
procd_set_param() { :; }
procd_close_instance() { :; }
ucode() { echo "ucode $*" >> "$TEST_LOG"; }
'''

    def invoke(command, running='0', enabled='0'):
        log.write_text('')
        env = os.environ | {'TEST_LOG': str(log), 'TEST_RUNNING': running, 'TEST_ENABLED': enabled}
        result = subprocess.run(['sh', '-c', init + stubs + '\n' + command], env=env, capture_output=True, text=True)
        return result.returncode, log.read_text().splitlines()

    # Even an existing directory left by an old RPC must not make hotplug/reload run.
    (run / 'mwan4').mkdir()
    assert invoke('service_running')[0] != 0
    assert invoke('reload_service') == (0, [])
    assert invoke('boot') == (0, [])
    assert invoke('boot', enabled='1') == (0, ['start'])
    assert invoke('reload_service', running='1') == (0, ['stop', 'start'])
    marker = run / 'mwan4-rule-guard.stopped'
    marker.touch()
    assert invoke('service_running', running='1')[0] != 0
    assert invoke('reload_service', running='1') == (0, [])
    rc, actions = invoke('start_service')
    assert rc == 0 and not marker.exists() and actions[0:2] == ['preset ', 'config'], actions
    assert any('init_setup.uc' in action for action in actions)
    rc, actions = invoke('stop_service')
    assert rc == 0 and marker.exists() and 'guard --cleanup' in actions
    assert any('init_teardown.uc' in action for action in actions)

    # First boot closes an inherited running service once; no policies are rewritten.
    board = temp / 'board'
    board.write_text('gemtek,xg2010g\n')
    control = temp / 'init-control'
    control.write_text('#!/bin/sh\necho "$1" >> "$TEST_LOG"\n'
                       '[ "$1" != status ] || [ "$TEST_RUNNING" = 1 ]\n')
    control.chmod(0o755)
    firstboot = (repo / 'files/etc/uci-defaults/99-xg2010g-mwan4-default-off').read_text()
    firstboot = firstboot.replace('/tmp/sysinfo/board_name', str(board)).replace('/etc/init.d/mwan4', str(control))
    firstboot = firstboot.replace('/var/run', str(run))
    for running, expected in [('0', ['status', 'disable']), ('1', ['status', 'stop', 'disable'])]:
        log.write_text('')
        subprocess.run(['sh', '-c', firstboot], check=True,
                       env=os.environ | {'TEST_LOG': str(log), 'TEST_RUNNING': running})
        assert log.read_text().splitlines() == expected
        assert marker.exists()
    assert not (root / 'files/etc/uci-defaults/98-xg2010g-mwan4-defaults').exists()
    assert (root / 'files/usr/libexec/xg2010g-mwan4-preset').stat().st_mode & 0o111
    assert (backend / 'files/etc/config/mwan4').read_bytes() == (repo / 'files/etc/config/mwan4').read_bytes()
    assert (root / 'files/etc/config/mwan4').read_bytes() == (repo / 'files/etc/config/mwan4').read_bytes()
    assert not (root / 'files/usr/share/xg2010g/mwan4-stock.config').exists()

    # Run the actual ucode RPC method with command capture, no host service access.
    rpc = (backend / 'files/usr/share/rpcd/ucode/mwan4').read_text()
    assert 'm.init();' not in rpc and 'm.load();' in rpc
    ucode = os.environ.get('UCODE', '/workspace/scratch/ucode-native-build/ucode')
    assert Path(ucode).is_file(), 'ucode required for RPC lifecycle checks'
    program = '''let commands = [], active = false;
let system = function(command) { push(commands, command); return 0; };
let m = {
 reload_config: function() {},
 ubus_call: function() { return {mwan4:{instances:{rtmon_ipv4:{running:active}}}}; },
 uci_foreach: function(kind, cb) { cb({'.name':'wan',enabled:'1',track_ip:['192.0.2.1']}); },
 uci_bool: function(x) { return x == '1'; }, get_families: function() { return ['ipv4']; }
};
''' + function(rpc, 'runtime_summary') + '\n' + function(rpc, 'control_call') + '''
for (let action in ['start', 'stop', 'restart']) {
 let r = control_call({args:{action,interface:null}});
 if (!r.ok) exit(1);
}
let before = length(commands);
let r = control_call({args:{action:'ifup',interface:'wan'}});
if (r.ok || length(commands) != before) exit(2);
active = true;
r = control_call({args:{action:'ifup',interface:'wan'}});
if (!r.ok) exit(3);
printf('%J\\n',commands);
'''
    path = temp / 'rpc.uc'
    path.write_text(program)
    commands = json.loads(subprocess.check_output([ucode, str(path)], text=True))
    assert 'enable && /etc/init.d/mwan4 start' in commands[0]
    assert 'disable && /etc/init.d/mwan4 stop' in commands[1]
    assert 'enable && /etc/init.d/mwan4 restart' in commands[2]

    overview = (frontend / 'htdocs/luci-static/resources/view/mwan4/network/overview.js').read_text()
    js = '''const assert = require('node:assert/strict');
let sequence, changes, notifications, rendered;
let hasOperatorAccess = true;
const _ = x => x;
const E = (tag, attrs, children) => ({tag,attrs,children});
const ui = {addNotification:(x,node)=>notifications.push(node.attrs[0])};
const byId = () => null;
const withBusy = (node,fn) => fn();
const withButtonBusy = (node,fn) => fn();
const eventButton = x => x;
const L = {resolveDefault:(value,fallback)=>Promise.resolve(value).catch(()=>fallback)};
const callStatus = () => Promise.resolve({diagnostics:{service_running:sequence.length>1?sequence.shift():sequence[0]}});
const uci = {save:()=>{changes.push('save');return Promise.resolve();},apply:()=>Promise.resolve(),unload:()=>{},load:()=>Promise.resolve()};
const runMwan4 = (args) => {changes.push(args[0]);return Promise.resolve(true);};
const renderApp = () => null;
const refreshRuntime = () => {changes.push('refresh');return Promise.resolve();};
''' + function(overview, 'saveApplyRestart') + '\n' + function(overview, 'renderServiceActions') + '''
(async () => {
 for (const [states, restarts] of [[[false,false,false],0],[[true,true,true],1],[[true,false,false],0]]) {
  sequence=[...states];changes=[];notifications=[];
  await saveApplyRestart();
  assert.equal(changes.filter(x=>x==='restart').length,restarts);
  if(states.at(-1)===false) assert.match(notifications.at(-1),/remains stopped/);
 }
 sequence=[null];changes=[];notifications=[];
 await assert.rejects(saveApplyRestart(),/Cannot determine/);
 assert.deepEqual(changes,[]);
 changes=[];rendered=renderServiceActions();
 await rendered.children[0].attrs.click({});
 assert.deepEqual(changes,['refresh']);
 console.log('PASS: stopped/running/apply-race/unknown-state/refresh UI paths');
})().catch(e=>{console.error(e);process.exit(1);});
'''
    path = temp / 'ui.js'
    path.write_text(js)
    subprocess.run(['node', str(path)], check=True)
print('PASS: first-boot stop, real procd state, stale directory, boot/reload gates, manual start/stop and persisted RPC controls')
