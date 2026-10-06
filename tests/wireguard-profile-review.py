"""Check WireGuard is excluded only for XG2010G, not other board profiles."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
profile = (repo / 'configs/gemtek_xg2010g.config').read_text()
generic = (repo / 'configs/an7581.config').read_text()
packages = ['kmod-wireguard', 'luci-proto-wireguard', 'wireguard-tools']
for package in packages:
    assert not re.search(rf'^CONFIG_PACKAGE_{re.escape(package)}=y', profile, re.M), package
    assert re.search(rf'^# CONFIG_PACKAGE_{re.escape(package)} is not set$', profile, re.M), package
assert re.search(r'^CONFIG_PACKAGE_kmod-wireguard=y', generic, re.M)
required = (repo / 'configs/xg2010g-required-packages.txt').read_text().splitlines()
assert not set(packages) & set(required)
assert 'luci-app-natmode' not in required
assert not re.search(r'^CONFIG_PACKAGE_luci-app-natmode=y', profile, re.M)
checker = repo / 'scripts/check-xg2010g-packages.py'
workflow = (repo / '.github/workflows/build-ponwrt.yml').read_text()
assert 'STATUS_PLUGINS="luci-app-airoha-npu luci-app-pon-status"' in workflow
assert 'STATUS_PLUGINS="luci-app-airoha-npu luci-app-pon-status luci-app-natmode"' in workflow
assert 'for p in $STATUS_PLUGINS; do' in workflow
assert 'timeout 12m apt-get' in workflow and 'timeout 15m apt-get' in workflow
assert 'curl --connect-timeout 15 --max-time 180 --retry 2' in workflow
with tempfile.TemporaryDirectory(prefix='xg-wg-profile-') as d:
    path = Path(d) / 'config'
    baseline = ''.join(f'CONFIG_PACKAGE_{package}=y\n' for package in required)
    path.write_text(baseline + 'CONFIG_PACKAGE_kmod-wireguard=y\n' + profile)
    result = subprocess.run([sys.executable, str(checker), 'config', str(path)], capture_output=True)
    assert result.returncode == 1 and b'kmod-wireguard' in result.stdout
    path.write_text(baseline + profile)
    result = subprocess.run([sys.executable, str(checker), 'config', str(path)], capture_output=True)
    assert result.returncode == 0, result.stdout
print('PASS: XG2010G WireGuard and NAT UI disabled and guarded; AN7581 generic/other profiles unchanged')
