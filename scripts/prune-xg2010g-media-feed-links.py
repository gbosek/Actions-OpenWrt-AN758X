"""Exclude unused desktop/media menus from the pinned XG2010G build.

Only installed feed symlinks and generated package indexes are removed. Feed
sources remain intact. Refuse the operation if the loaded config selects any
excluded package, or a feed link has an unexpected target/type.
"""
from pathlib import Path
import argparse
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('root', type=Path)
parser.add_argument('--profile', required=True)
args = parser.parse_args()
if args.profile != 'gemtek_xg2010g':
    print('Media feed scope unchanged for profile:', args.profile)
    raise SystemExit(0)
root = args.root.resolve()
config = (root / '.config').read_text()
selected = set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=[ym]$', config, re.M))
links = []
blocked = set()
for feed, paths in [('video', None), ('packages', {'sound/mpd/Makefile', 'sound/squeezelite/Makefile'})]:
    index = (root / f'feeds/{feed}.index').read_text()
    for block in re.split(r'(?=^Source-Makefile:)', index, flags=re.M):
        match = re.match(rf'Source-Makefile: feeds/{feed}/([^\n]+)', block)
        if not match or (paths is not None and match[1] not in paths):
            continue
        names = re.findall(r'^Package: (.*)$', block, re.M)
        blocked.update(names)
        source = root / 'feeds' / feed / Path(match[1]).parent
        link = root / 'package/feeds' / feed / source.name
        if link.is_symlink():
            if link.resolve() != source.resolve():
                raise SystemExit(f'Unexpected feed link target: {link}')
            links.append(link)
        elif link.exists():
            raise SystemExit(f'Refusing to remove a non-symlink: {link}')
if conflict := selected & blocked:
    raise SystemExit('XG2010G router feed scope excludes selected packages: ' + ', '.join(sorted(conflict)))
for link in set(links):
    link.unlink()
for name in ['.packageinfo', '.packagedeps', '.config-package.in']:
    (root / 'tmp' / name).unlink(missing_ok=True)
for pattern in ['.packageinfo-feeds_video_*', '.packageinfo-feeds_packages_mpd', '.packageinfo-feeds_packages_squeezelite']:
    for cached in (root / 'tmp/info').glob(pattern):
        cached.unlink()
print(f'XG2010G: excluded {len(set(links))} unused media feed links; sources and selected packages preserved')
