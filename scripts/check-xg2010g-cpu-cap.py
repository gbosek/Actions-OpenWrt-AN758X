"""Check the XG2010G CPU limit in the built FIT and prepared LuCI source."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

MAX_HZ = 1_400_000_000


def fdt(dtb, node, prop=None, kind=None):
    command = ['fdtget']
    if kind:
        command.extend(['-t', kind])
    if prop is None:
        command.extend(['-l', str(dtb), node])
    else:
        command.extend([str(dtb), node, prop])
    return subprocess.check_output(command, text=True).strip()


def check_dtb(dtb):
    assert 'gemtek,xg2010g' in fdt(dtb, '/', 'compatible').split(), 'wrong board'
    assert 'cpufreq.default_governor=powersave' in fdt(dtb, '/chosen', 'bootargs-append'), 'missing safe boot governor'
    table = '/opp-table'
    phandle = fdt(dtb, table, 'phandle', 'x')
    cpus = [node for node in fdt(dtb, '/cpus').split() if node.startswith('cpu@')]
    assert len(cpus) == 4, 'expected four AN7581 CPU cores'
    for cpu in cpus:
        assert fdt(dtb, '/cpus/' + cpu, 'operating-points-v2', 'x') == phandle, cpu
    frequencies = []
    for node in fdt(dtb, table).split():
        cells = [int(cell, 16) for cell in fdt(dtb, table + '/' + node, 'opp-hz', 'x').split()]
        assert len(cells) == 2, node
        frequencies.append((cells[0] << 32) | cells[1])
    assert frequencies and max(frequencies) == MAX_HZ, ('CPU OPP limit', frequencies)
    assert min(frequencies) == 500_000_000, ('CPU minimum', frequencies)
    assert len(frequencies) == len(set(frequencies)), 'duplicate CPU frequency'
    return sorted(frequencies)


def check_ui(path):
    constants = re.findall(r'\bvar\s+CPU_MAX_FREQ_KHZ\s*=\s*(\d+)\s*;', Path(path).read_text())
    assert constants == ['1400000'], ('CPU UI limit', constants)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('firmware', type=Path)
    parser.add_argument('--ui', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='xg2010g-cpu-cap-') as directory:
        dtb = Path(directory) / 'board.dtb'
        subprocess.run(['dumpimage', '-T', 'flat_dt', '-p', '1', '-o', str(dtb), str(args.firmware)],
                       check=True, stdout=subprocess.DEVNULL)
        frequencies = check_dtb(dtb)
    check_ui(args.ui)
    print(f'PASS: XG2010G FIT CPU max {max(frequencies) // 1_000_000} MHz, four cores, powersave boot, LuCI max 1400 MHz')


if __name__ == '__main__':
    main()
