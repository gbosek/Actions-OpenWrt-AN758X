#!/usr/bin/env python3
"""Enable the existing pre-ID reset path only for XG2010G's two 10G PHYs."""
from pathlib import Path
import hashlib, json, re, sys

repo = Path(__file__).resolve().parents[1]
meta = json.loads((repo / 'Boot/PHY-PRE-ID-SOURCE.json').read_text())

def install(root):
    support = root / meta['core_patch']
    assert support.is_file() and hashlib.sha256(support.read_bytes()).hexdigest() == meta['core_patch_sha256'], 'Unreviewed or missing baseline pre-ID reset support'
    duplicates = [p for p in (root / 'target/linux/generic').glob('*-6.18/*.patch')
                  if 'fwnode_mdiobus_reset_phy_before_id_read' in p.read_text(errors='replace')]
    assert duplicates == [support], 'Duplicate pre-ID reset implementation'
    path = root / meta['dts']
    text = path.read_text()
    for address, gpio in meta['phys'].items():
        pattern = r'(\b\w+:\s*ethernet-phy@' + address + r'\s*\{)([^{}]*)(\};)'
        found = list(re.finditer(pattern, text))
        assert len(found) == 1, 'Ambiguous XG2010G PHY node: ' + address
        node = found[0]; body = node[2]
        for field in [r'reg\s*=\s*<\s*' + address + r'\s*>',
                      r'reset-gpios\s*=\s*<\s*&en7581_pinctrl\s+' + str(gpio) + r'\s+GPIO_ACTIVE_LOW\s*>',
                      r'reset-assert-us\s*=\s*<\s*200000\s*>', r'reset-deassert-us\s*=\s*<\s*200000\s*>']:
            assert re.search(field + r'\s*;', body), 'Unexpected PHY GPIO/reset settings: ' + address
        count = body.count('reset-before-id-read')
        assert count <= 1 and (not count or re.search(r'\breset-before-id-read\s*;', body)), 'Conflicting pre-ID reset property'
        if not count:
            body, changed = re.subn(r'(\n([ \t]*)reset-deassert-us\s*=\s*<\s*200000\s*>\s*;)', r'\1\n\2reset-before-id-read;', body)
            assert changed == 1
        text = text[:node.start(2)] + body + text[node.end(2):]
    path.write_text(text)
    dest = root / 'files/etc/xg2010g-phy-pre-id-reset.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(meta, indent=2) + '\n')
    print('XG2010G PHY5/8: existing pre-ID reset enabled; GPIO and 200ms delays retained; CRC benefit not yet device-tested')

if __name__ == '__main__':
    install(Path(sys.argv[1]).resolve())
