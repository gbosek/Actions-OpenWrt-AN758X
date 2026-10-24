#!/usr/bin/env python3
"""Exercise the real fw4 template and request-driven module startup offline."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAYLOAD = REPO / 'Offload/bridge-defaults'


def run(argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, check=True, **kwargs).stdout


def check(fw4, ucode):
    with tempfile.TemporaryDirectory(prefix='bridge-default-') as tmp:
        root = Path(tmp)
        # Input is the source with upstream bridge support, before our package patch.
        for rel in ('root/usr/share/ucode/fw4.uc', 'root/usr/share/firewall4/templates/ruleset.uc'):
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fw4 / rel, dest)
        old = (root / 'root/usr/share/firewall4/templates/ruleset.uc').read_text()
        run(['patch', '-p1', '--fuzz=0', '-i', str(PAYLOAD / '002-xg2010g-bridge-flowtable-opt-in.patch')], cwd=root)
        code = (root / 'root/usr/share/ucode/fw4.uc').read_text()
        assert 'flow_offloading_bridge: [ "bool", "0" ]' in code
        template = root / 'root/usr/share/firewall4/templates/ruleset.uc'
        names = set(re.findall(r'fw4\.(\w+)\(', template.read_text()))
        functions = {
            'resolve_offload_devices': 'return ["lan1", "lan2", "pon0", "lan3"];',
            'resolve_bridge_devices': 'return ["lan1", "lan2", "lan4"];',
            'check_flowtable': 'return false;', 'check_bridge_flowtable': 'return false;',
            'default_option': 'return name == "flow_offloading_bridge" ? bridge : name == "flow_offloading_hw";',
            'includes': 'if (name == "ruleset-append") print("# custom bridge/ACL include preserved\\n");',
            'set': 'return "{ " + join(", ", map(name, x => sprintf("%J", x))) + " }";',
            'input_policy': 'return "drop";', 'forward_policy': 'return "drop";', 'output_policy': 'return "accept";',
        }
        script = root / 'render.uc'
        methods = ',\n'.join(n + ': function(name) { ' + functions.get(n, 'return [];') + ' }' for n in sorted(names))
        def render(path, enabled):
            script.write_text('{% let bridge = ' + ('true' if enabled else 'false') + '; let fw4 = {\n' + methods + '\n}; include(' + json.dumps(str(path)) + ', {fw4}); %}')
            return run([ucode, '-T', str(script)])
        original = root / 'old.uc'; original.write_text(old)
        before = render(original, True)
        disabled = render(template, False)
        enabled = render(template, True)
        assert 'table bridge fw4' not in disabled and 'flush table bridge' not in disabled
        assert 'table bridge fw4' in enabled and 'flowtable fb' in enabled
        assert 'flowtable ft' in disabled and 'flags offload;' in disabled
        assert 'policy drop;' in disabled and 'ct state vmap' in disabled
        assert '# custom bridge/ACL include preserved' in disabled
        assert before[:before.index('table bridge fw4')] == disabled[:disabled.index('# custom bridge/ACL include preserved')], 'inet rules changed'
        assert before.strip() == enabled.strip(), 'Explicit bridge FT mode changed'

        etc = root / 'etc'; (etc / 'sysctl.d').mkdir(parents=True)
        # Only filesystem names are redirected; execute the shipped helper body.
        helper = root / 'helper.sh'
        gate = root / 'gate'
        gate.write_text('0\n')
        helper.write_text((PAYLOAD / 'xg2010g-bridge-netfilter').read_text().replace('/etc/', str(etc) + '/').replace('/sys/kernel/debug/ppe/bridge_boot_ready', str(gate)))
        bindir = root / 'bin'; bindir.mkdir()
        calls = root / 'calls'
        (bindir / 'modprobe').write_text('#!/bin/sh\necho "$*" >> "$CALLS"\nexit "${MODPROBE_RESULT:-0}"\n')
        (bindir / 'logger').write_text('#!/bin/sh\nexit 0\n')
        for file in bindir.iterdir(): file.chmod(0o755)
        env = dict(os.environ, PATH=str(bindir) + ':' + os.environ['PATH'], CALLS=str(calls))
        def invoke(expected, rc=0):
            if calls.exists(): calls.unlink()
            result = subprocess.run(['sh', str(helper)], env=dict(env, MODPROBE_RESULT=str(rc)), capture_output=True)
            assert result.returncode == rc
            assert gate.read_text().strip() == ('0' if rc else '1'), 'Failed policy setup enabled fallback'
            assert calls.exists() == expected
            if expected: assert calls.read_text().strip() == 'br_netfilter'
        invoke(False)
        default = (fw4 / 'package/kernel/linux/files/sysctl-br-netfilter.conf').read_bytes()
        (etc / 'sysctl.d/11-br-netfilter.conf').write_bytes(default)
        invoke(False)
        custom = etc / 'sysctl.d/20-custom.conf'
        custom.write_text('net.ipv4.ip_forward=1\n# net.bridge.bridge-nf-call-iptables=1\n')
        invoke(False)
        custom.write_text('net.bridge.bridge-nf-call-iptables=1\n')
        invoke(True)
        invoke(True, 1)
        custom.write_text('net/bridge/bridge-nf-call-iptables=0\n')
        invoke(True)
        custom.unlink()
        (etc / 'sysctl.d/11-br-netfilter.conf').write_bytes(default + b'net.bridge.bridge-nf-call-iptables=1\n')
        invoke(True)
        assert (etc / 'sysctl.d/11-br-netfilter.conf').read_bytes() == default + b'net.bridge.bridge-nf-call-iptables=1\n'
        # Syntax check the exact shipped helper, with no target-side execution.
        run(['sh', '-n', str(PAYLOAD / 'xg2010g-bridge-netfilter')])
    return {'template_modes': 2, 'module_request_scenarios': 7, 'inet_output_unchanged': True,
            'custom_include_preserved': True, 'hardware_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fw4', type=Path, required=True)
    parser.add_argument('--ucode', required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.fw4, args.ucode)))
