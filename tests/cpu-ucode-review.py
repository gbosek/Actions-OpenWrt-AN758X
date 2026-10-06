"""Execute the actual CPU RPC method in the native OpenWrt ucode runtime."""
from pathlib import Path
import json
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
build = Path('/home/bosek/xg2010g-local-build/ponwrt-5615b88-clean')
runtime = build / 'staging_dir/hostpkg/bin/ucode'
files = [repo.parent / 'output/GitHub24-review/github-image/selected/usr/share/rpcd/ucode/luci', build / 'feeds/luci/modules/luci-base/root/usr/share/rpcd/ucode/luci']
cases = [
    (['cpu 0 0 0 0 0 0 0 0 0 0', 'cpu 1 0 0 499 0 0 0 0 0 0'], '0.2%'),
    (['cpu 0 0 0 0 0 0 0 0 0 0', 'cpu 25 0 0 75 0 0 0 0 0 0'], '25.0%'),
    (['cpu 0 0 0 0 0 0 0 0 0 0', 'cpu 100 0 0 0 0 0 0 0 0 0'], '100.0%'),
    (['cpu 0 0 0 0 0 0 0 0 0 0', 'cpu 0 0 0 100 0 0 0 0 0 0'], '0.0%'),
    (['cpu 0 0 0 0 0 0 0 0 0 0', 'cpu 0 0 0 75 0 0 0 25 0 0'], '25.0%'),
    (['cpu 0 0 0 0 0 0 0 0 0 0', 'cpu 25 0 0 75 0 0 0 0 25 0'], '25.0%'),
    (['bad', 'cpu 0 0 0 0 0 0 0 0 0 0'], '?'),
    (['cpu 0 0 0 0 0 0 0 0 0 0'] * 2, '?'),
    (['cpu 50 0 0 50 0 0 0 0 0 0', 'cpu 1 0 0 100 0 0 0 0 0 0'], '?'),
]
with tempfile.TemporaryDirectory(prefix='cpu-ucode-review-') as directory:
    for file in files:
        source = file.read_text()
        begin = source.index('\tgetCPUUsage: {')
        end = source.index('\n\tget', begin + 1)
        method = source[begin:end]
        script = 'let lines = []; function open(path, mode) { return { read: function(mode) { return shift(lines); }, close: function() {} }; } function sleep(ms) {}\nlet backend = {\n' + method + '\n};\n'
        for lines, expected in cases:
            script += 'lines = ' + json.dumps(lines) + '; print(backend.getCPUUsage.call().cpuusage, "\\n");\n'
        test = Path(directory) / 'cpu.uc'
        test.write_text(script)
        result = subprocess.check_output([str(runtime), str(test)], text=True).splitlines()
        assert result == [expected for _, expected in cases], (file, result)
print('PASS: GitHub #24 and updated CPU RPC in ucode: 0.2%, 25%, full/idle, steal, guest, malformed/no-progress/reset samples')
