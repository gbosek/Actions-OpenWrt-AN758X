#!/usr/bin/env python3
"""Install exactly one reviewed Airoha NPU plugin into a generated build tree."""
import argparse
import json
import shutil
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('--variant', choices=('naoki', 'luanmuc'), required=True)
a = p.parse_args()
repo = Path(__file__).resolve().parents[1]
origin = repo / 'Packages/NPU' / a.variant
app = origin / 'luci-app-airoha-npu'
meta = json.loads((origin / 'SOURCE.json').read_text())
assert (app / 'Makefile').is_file(), 'Selected package is absent'
root = a.source.resolve()
assert (root / 'target/linux/airoha').is_dir(), 'Expected an Airoha build source'
dest = root / 'package/custom/luci-app-airoha-npu'
assert dest.resolve() != app.resolve(), 'Source and destination must differ'
if dest.exists():
    shutil.rmtree(dest)
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(app, dest)
from adapt_npu import adapt
adapt(dest, a.variant)
meta["local_adjustments"].extend(["Shared kernel cpufreq policy adapter", "Compatibility boost enumeration and capability fields", "Local APK-compatible integer package revision", "Direct user-space PLL writes removed", "PPE complete export and snapshot/capability metadata", "Unused WiFi and jitter polling removed for XG2010G"])
meta["local_package_release"] = {"naoki": 910, "luanmuc": 104}[a.variant]
meta["local_adjustments"].append("State-aware PPE counters, preserved raw slot diagnostics, IB1/IB2/data and snapshot boot identity")
meta["local_adjustments"].append("Leave non-attributable PPE counter cells empty without modifying hardware or raw export")
meta["cpu_boost_source"] = "CPU-BOOST-SOURCE.json"
for file in (dest / 'root').rglob('*'):
    if file.is_file() and ('init.d' in file.parts or 'libexec' in file.parts) and file.suffix != '.awk':
        file.chmod(0o755)
(root / 'files/etc').mkdir(parents=True, exist_ok=True)
(root / 'files/etc/airoha-build-source.json').write_text(json.dumps(meta, indent=2) + '\n')
print(f"Selected {a.variant}: {meta['upstream']}@{meta['commit']} ({meta['upstream_version']})")
