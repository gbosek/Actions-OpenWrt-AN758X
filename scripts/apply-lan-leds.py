#!/usr/bin/env python3
"""Install the XG2010G PHY/GPIO link/activity LED mapping."""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
repo=Path(__file__).resolve().parents[1]
patch=repo/'Boot/xg2010g-lan34-leds.patch'
base=['patch','--batch','--forward','--fuzz=0','-p1','-d',str(root),'-i',str(patch)]
if subprocess.run(base+['--dry-run'],capture_output=True).returncode == 0:
    subprocess.run(base,check=True)
elif subprocess.run(base+['-R','--dry-run'],capture_output=True).returncode != 0:
    raise SystemExit('XG2010G LAN LED patch does not match this source')
relative='etc/uci-defaults/99-xg2010g-lan34-led-mode'
dest=root/'files'/relative
dest.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(repo/'Boot/root'/relative,dest)
dest.chmod(0o755)
(root/'files/etc/xg2010g-led-fixes.json').write_text(json.dumps({
    'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),
    'lan3':'EN8811H LED0 link, LED1 tx/rx',
    'lan4':'GPIO green link, yellow tx/rx',
    'hardware_visual_tested':False,
},indent=2)+'\n')
print('XG2010G: LAN3/LAN4 link/activity defaults and retained-settings migration installed')
