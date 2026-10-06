"""Reject a reintroduced high CPU OPP or UI limit before publishing a build."""
from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cpu_cap', repo / 'scripts/check-xg2010g-cpu-cap.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
patch = (repo / 'patches/target/airoha-xg2010g-cpu-opp.patch').read_text()
assert [int(value) for value in re.findall(r'^\+\s+opp-hz = /bits/ 64 <(\d+)>;', patch, re.M)] == [1_250_000_000, 1_300_000_000, 1_350_000_000, 1_400_000_000]
assert not re.search(r'smcc_opp(?:19|20|21|22)', patch)
assert 'cpufreq.default_governor=powersave' in patch
part1 = (repo / 'diy-part1.sh').read_text()
assert "^var CPU_MAX_FREQ_KHZ = 1400000;$" in part1
assert 'CPU_MAX_FREQ_KHZ = 1600000' not in part1
freq_patch = (repo / 'patches/target/airoha-cpufreq-default.patch').read_text()
assert 'uci_write_config 0 ondemand 500000 1200000 10 50' in freq_patch
assert 'uci_write_config 0 ondemand 500000 1400000 10 50' not in freq_patch
assert 'PKG_RELEASE:=4' in freq_patch
assert 'CPU_DEFAULT_MAX_FREQ_KHZ=1200000' in part1
assert "option max_freq '1200000'" in part1
assert '手动上限保留 1400 MHz' in part1

with tempfile.TemporaryDirectory(prefix='cpu-cap-review-') as directory:
    root = Path(directory)
    source = root / 'fixture.dts'
    dtb = root / 'fixture.dtb'
    ui = root / 'status.js'
    for maximum, safe in [(1_400_000_000, True), (1_600_000_000, True), (1_400_000_000, False)]:
        boot = 'cpufreq.default_governor=powersave' if safe else ''
        cpus = ''.join(f'cpu@{core} {{ operating-points-v2 = <&opps>; }};' for core in range(4))
        source.write_text(f'''/dts-v1/;
        / {{ compatible = "gemtek,xg2010g";
            chosen {{ bootargs-append = "{boot}"; }};
            cpus {{ {cpus} }};
            opps: opp-table {{
                opp-500 {{ opp-hz = /bits/ 64 <500000000>; }};
                opp-max {{ opp-hz = /bits/ 64 <{maximum}>; }};
            }};
        }};''')
        subprocess.run(['dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(dtb), str(source)], check=True)
        try:
            module.check_dtb(dtb)
        except AssertionError:
            assert maximum > module.MAX_HZ or not safe
        else:
            assert maximum == module.MAX_HZ and safe
    for constant, valid in [(1400000, True), (1600000, False)]:
        ui.write_text(f'var CPU_MAX_FREQ_KHZ={constant};')
        try:
            module.check_ui(ui)
        except AssertionError:
            assert not valid
        else:
            assert valid
print('PASS: CPU OPP/SMCC patch ceiling, four-core FIT DTB guard, powersave boot and source/minified UI cap')
