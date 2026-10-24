"""Native localhost Vivado synthesis and independent RAM INIT bit-plane audit.

Component evidence only. This never launches an FPGA build farm or an AFI job.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_initialized_bank_vcs import GENERATED, SOURCES
from tools.checkpoint_formats.tests.audit_ram_style import audit

ROOT = Path(__file__).resolve().parents[3]
TCL = 'tools/checkpoint_formats/capture_initialized_bank_synth.tcl'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_primitive_initialization(report):
    cells = re.findall(r'CELL (\S+) REF_NAME=(\S+)\n(.*?)(?=CELL |\Z)', report, re.S)
    # Each dual-port RAM32X1D contains a RAMD32 copy for each independent
    # asynchronous read port. Check both physical copies as well as the wrapper.
    require(len(cells) == 54, 'expected 18 dual-port planes and 36 physical read-port copies')
    seen = set()
    for cell, primitive, properties in cells:
        location = re.fullmatch(r'(a|b)/ram_reg_0_7_(\d+)_(\d+)(?:/(DP|SP))?', cell)
        require(location is not None, 'unexpected native RAM mapping')
        side, low, high, port = location.groups()
        require(primitive == ('RAMD32' if port else 'RAM32X1D'), 'unexpected native RAM primitive')
        require(re.search(r'^RAM_STYLE=distributed$', properties, re.M) is not None,
                f'emitted RAM-style constraint not applied to native memory {cell}')
        bit = int(low)
        require(low == high and bit < 9 and (side, bit, port) not in seen, 'duplicate or reshaped native RAM plane')
        seen.add((side, bit, port))
        value = re.search(r"^INIT=32'h([0-9a-fA-F]{8})$", properties, re.M)
        require(value is not None, 'missing native RAM INIT parameter')
        words = [17 + i * 29 if side == 'a' else 401 - i * 31 for i in range(8)]
        expected = sum(((word >> bit) & 1) << addr for addr, word in enumerate(words))
        require(int(value[1], 16) == expected, f'native initialized state mismatch at {cell}')
    return len(seen) // 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
            'run on native manager with HDK setup sourced first')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='initialized-vivado-', dir=base))
    snapshots = out / 'generated-snapshots'; snapshots.mkdir()
    for name in GENERATED:
        (snapshots / name).write_bytes((args.generated.resolve() / name).read_bytes())
    ram_style = audit(snapshots)
    sources = (*SOURCES, TCL, 'tools/checkpoint_formats/tests/synth_initialized_bank.py')
    for name in sources:
        dest = out / 'source-snapshots' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
    script = out / 'source-snapshots' / TCL
    argv = ['vivado', '-mode', 'batch', '-source', str(script), '-log', 'vivado.log',
            '-journal', 'vivado.jou', '-tclargs', str(snapshots), str(out)]
    command = dict(argv=argv, cwd=str(out), log=str(out / 'command.log'))
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'command.log').open('w') as stream:
        result = subprocess.run(argv, cwd=out, stdout=stream, stderr=subprocess.STDOUT)
    command['returncode'] = result.returncode
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    require(result.returncode == 0 and 'INITIALIZED_BANK_SYNTH_PASS' in (out / 'command.log').read_text(),
            f'Vivado incomplete; inspect {out / "command.log"}')
    planes = audit_primitive_initialization((out / 'initialization.rpt').read_text())
    with zipfile.ZipFile(out / 'InitializedStorage.dcp') as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for text in ('<Part Name="xcvu47p-fsvh2892-2-e"', '<Top Name="InitializedStorage"',
                     '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(text in metadata, 'native DCP identity: ' + text)
        require(len(dcp.read('InitializedStorage.edf')) > 0, 'empty native netlist')
    utilization = (out / 'utilization.rpt').read_text()
    luts = int(re.search(r'\| CLB LUTs\*\s*\|\s*(\d+)\s*\|', utilization)[1])
    registers = int(re.search(r'\| CLB Registers\s*\|\s*(\d+)\s*\|', utilization)[1])
    names = ('InitializedStorage.dcp', 'utilization.rpt', 'timing.rpt', 'vivado.log', 'vivado.jou',
             'command.log', 'command.json', 'initialization.rpt', 'native-functional.v')
    require(all((out / name).stat().st_size > 0 for name in names), 'missing native evidence')
    summary = dict(status='pass', backend='f2', original_root=str(ROOT), host=socket.gethostname(),
                   observed_utc=datetime.now(timezone.utc).isoformat(), physical_fpga_capture=False,
                   full_rocket_image_build=False, scope='native initialized RAM bank component OOC synthesis only',
                   luts=luts, registers=registers, initialized_bit_planes=planes,
                   ram_style=ram_style,
                   initialized_physical_read_port_copies=planes * 2, command=command,
                   constrained_native_ram_cells=planes * 3,
                   sources={n: sha(out / 'source-snapshots' / n) for n in sources},
                   generated={n: sha(snapshots / n) for n in GENERATED},
                   artifacts={n: sha(out / n) for n in names})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
