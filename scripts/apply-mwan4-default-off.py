#!/usr/bin/env python3
"""Keep MWAN4 stopped until an explicit start; preserve that state on edits."""
import json
import re
import sys
from pathlib import Path


def replace_once(path, old, new):
    text = path.read_text()
    if new in text:
        return
    assert text.count(old) == 1, 'MWAN4 source changed: ' + str(path)
    path.write_text(text.replace(old, new, 1))


def install(root):
    repo = Path(__file__).resolve().parents[1]
    backend = root / 'package/custom/mwan4'
    frontend = root / 'package/custom/luci-app-mwan4'
    init = backend / 'files/etc/init.d/mwan4'
    assert init.is_file() and frontend.is_dir(), 'Pinned MWAN4 packages missing'
    replace_once(init, 'service_running() {\n\t[ -d "$MWAN4_STATUS_DIR" ]\n}',
                 'service_running() {\n\t[ ! -e /var/run/mwan4-rule-guard.stopped ] &&\n'
                 '\t\tprocd_running mwan4 "${1:-*}"\n}')
    replace_once(init, 'reload_service() {\n\tstop\n\tstart\n}',
                 'reload_service() {\n\t# Applying configuration must not start a stopped service.\n'
                 '\tservice_running || return 0\n\tstop\n\tstart\n}')
    replace_once(init, 'service_triggers() {',
                 'boot() {\n\t# A boot queue may still contain a link removed by first-boot defaults.\n'
                 '\tenabled || return 0\n\tstart\n}\n\nservice_triggers() {')
    replace_once(init, '\tconfig_load mwan4\n',
                 '\t# Apply an untouched preset only when MWAN4 is requested.\n'
                 '\t/usr/libexec/xg2010g-mwan4-preset || return 1\n\tconfig_load mwan4\n')
    replace_once(init, '|| /usr/bin/mwan4-rule-guard.sh --routes-only',
                 '|| MWAN4_STARTUP=init /usr/bin/mwan4-rule-guard.sh --routes-only')
    rpc = backend / 'files/usr/share/rpcd/ucode/mwan4'
    replace_once(rpc, 'm.init();', 'm.load(); // Reading status must not create running-state directories.')
    replace_once(rpc, "command = '/etc/init.d/mwan4 ' + action;",
                 "let persistence = action == 'stop' ? 'disable' : 'enable';\n"
                 "        command = '/etc/init.d/mwan4 ' + persistence + ' && /etc/init.d/mwan4 ' + action;")
    replace_once(rpc, "} else if (action == 'ifup' || action == 'ifdown') {",
                 "} else if (action == 'ifup' || action == 'ifdown') {\n"
                 "        if (!runtime_summary().service_running)\n"
                 "            return { ok: false, errors: [{ message: 'Start MWAN4 before changing WAN link state' }] };")

    overview = frontend / 'htdocs/luci-static/resources/view/mwan4/network/overview.js'
    replace_once(overview,
                 "'Refresh MultiWAN 4 runtime'), 'aria-busy': 'false', click: function(ev) { return runMwan4([ 'restart' ], eventButton(ev)); }",
                 "'Refresh MultiWAN 4 runtime'), 'aria-busy': 'false', click: function(ev) { return withButtonBusy(eventButton(ev), refreshRuntime).catch(function(e) { ui.addNotification(null, E('p', [ e.message || String(e) ]), 'danger'); }); }")
    text = overview.read_text()
    start = text.index('function saveApplyRestart() {')
    end = text.index('\nfunction closeModal()', start)
    text = text[:start] + '''function saveApplyRestart() {
	let root = byId('mwan4-app');
	let wasRunning = false;
	let restarted = false;
	function running(status) {
		let value = ((status || {}).diagnostics || {}).service_running;
		if (typeof value != 'boolean')
			throw new Error(_('Cannot determine MultiWAN 4 service state.'));
		return value;
	}

	return withBusy(root, function() { return callStatus()
		.then(function(status) { wasRunning = running(status); return uci.save(); })
		.then(function() { return uci.apply(10); })
		.then(function() { return callStatus(); })
		.then(function(status) {
			// A stopped service, including one stopped during apply, stays stopped.
			if (!wasRunning || !running(status) || !hasOperatorAccess)
				return;
			return runMwan4([ 'restart' ]).then(function(ok) {
				if (ok !== true)
					throw new Error(_('Control request failed'));
				restarted = true;
			});
		})
		.then(function() { return callStatus(); })
		.then(function(status) {
			let message = restarted ? _('MultiWAN 4 settings applied and service restarted.')
				: running(status) ? _('MultiWAN 4 settings applied.')
				: _('MultiWAN 4 settings applied. Service remains stopped.');
			ui.addNotification(null, E('p', [ message ]), 'info');
			uci.unload([ 'mwan4', 'network' ]);
			return Promise.all([ uci.load('mwan4'), uci.load('network'), L.resolveDefault(callStatus(), {}) ]);
		})
		.then(function(data) {
			if (root)
				root.replaceChildren(renderApp(data[2] || {}));
		});
	});
}
''' + text[end:]
    overview.write_text(text)
    translations = {
        'Cannot determine MultiWAN 4 service state.': '无法确定 MWAN4 服务状态。',
        'MultiWAN 4 settings applied.': 'MWAN4 设置已应用。',
        'MultiWAN 4 settings applied. Service remains stopped.': 'MWAN4 设置已应用，服务保持停止。',
    }
    for relative, translated in [('po/templates/mwan4.pot', False), ('po/zh_Hans/mwan4.po', True)]:
        path = frontend / relative
        text = path.read_text()
        for message, chinese in translations.items():
            if 'msgid ' + json.dumps(message) not in text:
                text += '\nmsgid ' + json.dumps(message) + '\nmsgstr ' + json.dumps(chinese if translated else '', ensure_ascii=False) + '\n'
        path.write_text(text)
    for package, release in [(backend, 8), (frontend, 12)]:
        make = package / 'Makefile'
        text, count = re.subn(r'^PKG_RELEASE:=.*$', 'PKG_RELEASE:=' + str(release), make.read_text(), flags=re.M)
        assert count == 1
        make.write_text(text)
    legacy = root / 'files/etc/uci-defaults/98-xg2010g-mwan4-defaults'
    legacy.unlink(missing_ok=True)
    output = root / 'files/etc/xg2010g-mwan4-source.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((repo / 'MWAN4-SOURCE.json').read_bytes())
    print('MWAN4: explicit start/stop controls boot state; reload/apply/refresh preserve stopped state')


if __name__ == '__main__':
    install(Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve())
