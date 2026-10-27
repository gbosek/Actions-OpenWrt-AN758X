#!/usr/bin/env python3
"""Retain compatible feeds and R68 while changing only the offload path."""
import argparse, json, re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
root = p.parse_args().source
ref = 'e5194d2dfd169eef8f4a944fdc3f929e0287b680'
repo = Path(__file__).resolve().parents[1]
metadata = json.loads((repo/'BASELINE-FEEDS.json').read_text())
config = root/'feeds.conf.default'
text = config.read_text()
selected = {}
for name, source in metadata['feeds'].items():
    pattern = r'^(src-git\s+'+re.escape(name)+r'\s+)(\S+)[^\n]*$'
    matches = list(re.finditer(pattern, text, re.M))
    assert len(matches) == 1, 'Expected one reviewed feed: '+name
    location = matches[0][2]
    url = re.split(r'[;^]', location)[0].removesuffix('.git')
    expected = source['url'].removesuffix('.git')
    if name == 'pon_userspace' and url == metadata['naoki_onu_override']['url'].removesuffix('.git'):
        source = metadata['naoki_onu_override']
        assert location.endswith('^'+source['commit']), 'Unreviewed naoki ONU override'
    else:
        assert url == expected, 'Refusing unknown feed source: '+name
    text = re.sub(pattern, lambda m: m[1]+source['url']+'^'+source['commit'], text, flags=re.M)
    selected[name] = source
assert selected['pon_drivers']['commit'] == ref
config.write_text(text)
dest = root/'files/etc/pon-driver-build-source.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps({'repo':'pbs05/openwrt-pon-drivers', 'commit':ref, 'xpon_release':68,
    'reason':'Retain the R68 driver from the delivered 20261018 runtime-led image; no unrelated PON driver upgrade'}, indent=2)+'\n')
(root/'files/etc/firmware-feed-pins.json').write_text(json.dumps({'basis':metadata['basis'], 'selected':selected}, indent=2)+'\n')
print('Retained PON driver R68 at', ref)
print('Pinned compatible baseline feeds and reviewed ONU selection; optional Argon override is separately verified')
