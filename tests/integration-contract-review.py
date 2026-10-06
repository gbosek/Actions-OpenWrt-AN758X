"""Exercise build defaults and the package contract without changing a router."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
checker = repo / 'scripts/check-xg2010g-packages.py'
spec = importlib.util.spec_from_file_location('contract', checker)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
required = [s.strip() for s in (repo / 'configs/xg2010g-required-packages.txt').read_text().splitlines() if s.strip() and not s.startswith('#')]
assert len(required) == len(set(required))
with tempfile.TemporaryDirectory(prefix='xg-integration-') as directory:
    root = Path(directory)
    formats = {'config': 'CONFIG_PACKAGE_{}=y\n', 'index': 'Package: {}\n', 'manifest': '{} - 1.0-r1\n', 'installed': 'P:{}\nV:1.0-r1\n\n'}
    for stage, template in formats.items():
        contents = ''.join(template.format(p) for p in required)
        path = root / stage
        path.write_text(contents)
        result = subprocess.run([sys.executable, str(checker), stage, str(path)], capture_output=True)
        assert result.returncode == 0, result.stdout
        path.write_text(contents.replace(template.format('mtr-json'), ''))
        result = subprocess.run([sys.executable, str(checker), stage, str(path)], capture_output=True)
        assert result.returncode == 1 and b'mtr-json' in result.stdout
        path.write_text(contents + template.format('luci-app-pon'))
        result = subprocess.run([sys.executable, str(checker), stage, str(path)], capture_output=True)
        assert result.returncode == (0 if stage == 'index' else 1)
        for package in ['luci-proto-wireguard', 'wireguard-tools', 'kmod-wireguard', 'luci-app-natmode']:
            path.write_text(contents + template.format(package))
            result = subprocess.run([sys.executable, str(checker), stage, str(path)], capture_output=True)
            assert result.returncode == (0 if stage == 'index' else 1), (stage, package, result.stdout)
    config = root / 'config'
    config.write_text('CONFIG_PACKAGE_luci-proto-wireguard=m\n')
    result = subprocess.run([sys.executable, str(checker), 'config', str(config)], capture_output=True)
    assert result.returncode == 1 and b'luci-proto-wireguard' in result.stdout
    for profile in ['gemtek_xg2010g', 'znxt_zn515xg-d']:
        work = root / profile
        (work / 'files/etc/uci-defaults').mkdir(parents=True)
        (work / '.config').write_text('# CONFIG_PACKAGE_iw is not set\n')
        (work / 'files/etc/uci-defaults/96-wifi-5g-cn').write_text('old wireless overlay')
        result = subprocess.run(['bash', str(repo / 'diy-part2.sh')], cwd=work, env=dict(os.environ, PROFILE=profile), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        timezone = work / 'files/etc/uci-defaults/99-timezone-cn'
        assert timezone.exists() and "timezone='CST-8'" in timezone.read_text() and '/etc/init.d/system reload' in timezone.read_text()
        if profile == 'gemtek_xg2010g':
            assert not (work / 'files/etc/uci-defaults/96-wifi-5g-cn').exists()
            assert 'CONFIG_PACKAGE_iw=y' not in (work / '.config').read_text()
        else:
            assert (work / 'files/etc/uci-defaults/96-wifi-5g-cn').exists()
            assert 'CONFIG_PACKAGE_iw=y' in (work / '.config').read_text()
    part1 = (repo / 'diy-part1.sh').read_text()
    assert part1.index('cp -a "$PON_STATUS_SRC"') < part1.index('make -s prepare-tmpinfo')
    assert 'prepare-tmpinfo OPENWRT_BUILD= 2>&1 | tail -5 || true' not in part1
    assert '2609164ff608ee4e6ac7e63fd5896176805bd9ed' in part1
    workflow = (repo / '.github/workflows/build-ponwrt.yml').read_text()
    assert 'cp -a "$GITHUB_WORKSPACE/files/." files/' in workflow
    assert 'check-xg2010g-packages.py" config' in workflow
    assert 'check-xg2010g-packages.py" manifest' in workflow
    assert 'check-xg2010g-cpu-cap.py" "$firmware"' in workflow
    assert '-name \'*gemtek_xg2010g.manifest\'' not in workflow
    assert '"${#manifests[@]}" -ne 1' in workflow
print('PASS: package contract at four stages, missing/legacy packages rejected, local PON indexing order, NOWIFI and Wi-Fi profiles, timezone owner and overlay copy')
