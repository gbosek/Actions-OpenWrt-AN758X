"""Guard the 1200 MHz reset default and persistence across both boot services."""
from pathlib import Path
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
default_patch = (repo / 'patches/target/airoha-cpufreq-default.patch').read_text(encoding='utf-8')
persist_patch_path = repo / 'patches/airoha/100-cpu-persist-cpufreq-config.patch'
persist_patch = persist_patch_path.read_text(encoding='utf-8')
part1 = (repo / 'diy-part1.sh').read_text(encoding='utf-8')

assert 'uci_write_config 0 ondemand 500000 1200000 10 50' in default_patch
assert 'CPU_DEFAULT_MAX_FREQ_KHZ=1200000' in part1
assert "option max_freq '1200000'" in part1
assert "var CPU_MAX_FREQ_KHZ = 1400000;" in part1
assert 'uci -q set cpufreq.cpufreq.governor0="$1"' in persist_patch
assert 'uci -q set cpufreq.cpufreq.maxfreq0="$2"' in persist_patch
assert "uci -q set cpufreq.global.set='1'" in persist_patch
assert 'uci commit airoha_npu || return 1' in persist_patch
assert 'uci commit cpufreq' in persist_patch
assert 'CPU_PERSIST_PATCH' in part1 and 'apply_source_patch_once "$CPU_PERSIST_PATCH" "$PKG_DIR"' in part1
subprocess.run([sys.executable, str(repo / 'scripts/validate-unified-diff.py'), str(persist_patch_path)], check=True)
print('PASS: factory/reset default 1200 MHz, selectable ceiling 1400 MHz and both reboot configurations stay synchronized')
