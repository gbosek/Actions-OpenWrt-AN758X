#!/usr/bin/env python3
"""Retain the delivered PON driver while changing only the offload path."""
import argparse, json, re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
root = p.parse_args().source
ref = 'e5194d2dfd169eef8f4a944fdc3f929e0287b680'
config = root/'feeds.conf.default'
text = config.read_text()
pattern = r'^(src-git\s+pon_drivers\s+https://github\.com/pbs05/openwrt-pon-drivers(?:\.git)?)(?:[;^]\S+)?\s*$'
text, count = re.subn(pattern, lambda m: m[1]+'^'+ref, text, flags=re.M)
assert count == 1, 'Expected exactly one reviewed PON driver feed; refusing to replace unknown source'
config.write_text(text)
dest = root/'files/etc/pon-driver-build-source.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps({'repo':'pbs05/openwrt-pon-drivers', 'commit':ref, 'xpon_release':68,
    'reason':'Retain the R68 driver from the delivered 20261018 runtime-led image; no unrelated PON driver upgrade'}, indent=2)+'\n')
print('Retained PON driver R68 at', ref)
