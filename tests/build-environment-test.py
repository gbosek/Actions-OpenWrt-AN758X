#!/usr/bin/env python3
"""Execute the host setup with mock commands, including failure propagation."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
script = repo / 'scripts/init_build_environment.sh'
workflow = (repo / '.github/workflows/build-ponwrt.yml').read_text()
assert 'python3-distutils' not in script.read_text()
assert 'build-scripts.immortalwrt.org' not in workflow
assert 'timeout-minutes: 25' in workflow
assert 'bash "$GITHUB_WORKSPACE/scripts/init_build_environment.sh"\n' in workflow
with tempfile.TemporaryDirectory(prefix='build-environment-') as directory:
    root = Path(directory)
    log = root / 'commands.jsonl'
    for name, text in {
        'sudo': '#!/bin/sh\n[ "$1" != -E ] || shift\nexec "$@"\n',
        'timeout': '#!/bin/sh\nshift 3\nexec "$@"\n',
        'apt-get': '''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['APT_TEST_LOG'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
if os.environ.get('APT_FAIL') in sys.argv[1:]:sys.exit(42)
''',
    }.items():
        path = root / name
        path.write_text(text)
        path.chmod(0o755)
    env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'], APT_TEST_LOG=str(log))
    subprocess.run(['bash', '-n', str(script)], check=True)
    subprocess.run(['bash', str(script)], env=env, check=True)
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(commands) == 2 and 'update' in commands[0] and 'install' in commands[1]
    assert '--no-install-recommends' in commands[1] and 'python3-setuptools' in commands[1]
    assert all('Acquire::Retries=2' in c and 'DPkg::Lock::Timeout=120' in c for c in commands)
    assert not any('texlive' in arg or arg == 'full-upgrade' for c in commands for arg in c)
    for operation in ('update', 'install'):
        log.unlink()
        result = subprocess.run(['bash', str(script)], env=dict(env, APT_FAIL=operation))
        assert result.returncode == 42
        assert len(log.read_text().splitlines()) == (1 if operation == 'update' else 2)
print('PASS: bounded local dependency setup, no recommends/remote upgrades, update/install failures propagate')
