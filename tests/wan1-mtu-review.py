"""Check WAN1 MTU hunk against the function reconstructed from pinned patches.

This checks patch context and register-field separation, not kernel compilation.
The two reference patches are saved in output/GitHub24-review from GitHub.
"""
from pathlib import Path
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
review = repo.parent / 'output/GitHub24-review'
first = (review / '920-13.patch').read_text(encoding='utf-8')
second = (review / '920-16.patch').read_text(encoding='utf-8')
begin = first.index('+static void airoha_dev_set_mtu(')
end = first.index('\n+}', begin) + len('\n+}')
function = '\n'.join(line[1:] for line in first[begin:end].splitlines()) + '\n'
old = '\t\t\t      FIELD_PREP(WAN_MTU0_MASK, netdev->mtu));'
new = '\t\t\t      FIELD_PREP(WAN_MTU0_MASK, netdev->mtu + VLAN_ETH_HLEN));'
assert '-' + old in second and '+' + new in second
function = function.replace(old, new)
patch = repo / 'patches/xg2010g/939-net-airoha-program-mtu-for-runtime-wan1.patch'
text = patch.read_text(encoding='utf-8')
hunk = text[text.index('\n@@ '):].splitlines()[2:]
before = '\n'.join(line[1:] for line in hunk if line.startswith((' ', '-'))) + '\n'
after = '\n'.join(line[1:] for line in hunk if line.startswith((' ', '+'))) + '\n'
assert function.count(before) == 1, 'hunk does not match pinned MTU function'
updated = function.replace(before, after)
assert updated.count('airoha_ppe_set_mtu(dev);') == 1
assert 'else if (!airoha_is_lan_gdm_dev(dev))' in updated
assert 'REG_WAN_MTU1' not in updated
assert 'FIELD_PREP(WAN_MTU1_MASK, netdev->mtu + VLAN_ETH_HLEN)' in updated
# Check native git's patch parser and exact application to the reconstructed function.
with tempfile.TemporaryDirectory(dir=review) as directory:
    root = Path(directory)
    source = root / 'drivers/net/ethernet/airoha/airoha_eth.c'
    source.parent.mkdir(parents=True)
    source.write_text('\n' * 2110 + function, encoding='utf-8', newline='\n')
    subprocess.run(['git', 'apply', '--check', '--verbose', str(patch)], cwd=root, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=root, check=True)
    assert source.read_text().endswith(updated)
for mtu in (1500, 2000, 9220):
    original = 0xC0000000 | 1518 | (1514 << 16)
    mask = 0x3FFF << 16
    result = (original & ~mask) | ((mtu + 18) << 16)
    assert result & 0x3FFF == 1518, 'WAN0 MTU changed'
    assert (result >> 16) & 0x3FFF == mtu + 18
    assert result & 0xC0000000 == original & 0xC0000000
print('PASS: pinned MTU context, git patch application and independent WAN1/WAN0 fields')
