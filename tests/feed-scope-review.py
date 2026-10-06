"""Check link-only pruning, configuration guards and silent Kconfig failures."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
prune = repo / 'scripts/prune-xg2010g-media-feed-links.py'
with tempfile.TemporaryDirectory(prefix='xg-feed-review-') as directory:
    root = Path(directory)
    (root / 'tmp/info').mkdir(parents=True)
    (root / 'feeds/video/frameworks/qt5base').mkdir(parents=True)
    (root / 'feeds/packages/sound/mpd').mkdir(parents=True)
    (root / 'feeds/packages/sound/squeezelite').mkdir(parents=True)
    (root / 'feeds/packages/net/etherwake').mkdir(parents=True)
    (root / 'feeds/video.index').write_text('Source-Makefile: feeds/video/frameworks/qt5base/Makefile\nPackage: qt5base-gui\n')
    (root / 'feeds/packages.index').write_text('Source-Makefile: feeds/packages/sound/mpd/Makefile\nPackage: mpd-full\n\nSource-Makefile: feeds/packages/sound/squeezelite/Makefile\nPackage: squeezelite-custom\n\nSource-Makefile: feeds/packages/net/etherwake/Makefile\nPackage: etherwake\n')
    for feed, source in [('video', 'frameworks/qt5base'), ('packages', 'sound/mpd'), ('packages', 'sound/squeezelite'), ('packages', 'net/etherwake')]:
        parent = root / 'package/feeds' / feed
        parent.mkdir(parents=True, exist_ok=True)
        (parent / Path(source).name).symlink_to(root / 'feeds' / feed / source, target_is_directory=True)
    video_link = root / 'package/feeds/video/qt5base'
    (root / '.config').write_text('CONFIG_PACKAGE_qt5base-gui=m\n')
    result = subprocess.run([sys.executable, str(prune), str(root), '--profile', 'other'], capture_output=True)
    assert result.returncode == 0 and video_link.is_symlink()
    result = subprocess.run([sys.executable, str(prune), str(root), '--profile', 'gemtek_xg2010g'], capture_output=True)
    assert result.returncode != 0 and video_link.is_symlink()
    (root / '.config').write_text('CONFIG_PACKAGE_etherwake=y\n')
    for attempt in range(2):
        result = subprocess.run([sys.executable, str(prune), str(root), '--profile', 'gemtek_xg2010g'], capture_output=True)
        assert result.returncode == 0, result.stderr
    assert not video_link.exists()
    assert (root / 'feeds/video/frameworks/qt5base').is_dir()
    assert (root / 'feeds/packages/sound/mpd').is_dir()
    assert (root / 'package/feeds/packages/etherwake').is_symlink()
    video_link.mkdir()
    result = subprocess.run([sys.executable, str(prune), str(root), '--profile', 'gemtek_xg2010g'], capture_output=True)
    assert result.returncode != 0 and video_link.is_dir()
    fake_bin = root / 'bin'
    fake_bin.mkdir()
    make = fake_bin / 'make'
    env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ['PATH'])
    for body, code in [('echo "No change to .config"; exit 0', 0),
                       ('echo "tmp/.config-package.in:12:error: recursive dependency detected!"; exit 0', 1),
                       ('echo "build failed"; exit 2', 2)]:
        make.write_text('#!/bin/bash\n' + body + '\n')
        make.chmod(0o755)
        result = subprocess.run(['bash', str(repo / 'scripts/defconfig-checked.sh')], cwd=root, env=env, capture_output=True)
        assert result.returncode == code, result.stdout
print('PASS: only unused media links removed, sources retained, selected packages and other profiles protected, repeat safe, non-links refused, silent Kconfig errors fail')
