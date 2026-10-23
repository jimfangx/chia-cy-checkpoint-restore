"""Native localhost Vivado synthesis of complete wide/deep fixture storage."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_chunked_bank_vcs import GENERATED, SOURCES, sha

ROOT = Path(__file__).resolve().parents[3]
TCL = 'tools/checkpoint_formats/capture_chunked_bank_synth.tcl'


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
    out = Path(tempfile.mkdtemp(prefix='chunked-vivado-', dir=base))
    snapshots = out / 'generated-snapshots'; snapshots.mkdir()
    for name in GENERATED:
        dest = snapshots / name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((args.generated.resolve() / name).read_bytes())
    sources = (*SOURCES, TCL, 'tools/checkpoint_formats/tests/synth_chunked_bank.py')
    for name in sources:
        dest = out / 'source-snapshots' / name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
    for name in ('deep.hex', 'wide.hex'):
        (out / name).write_bytes((snapshots / name).read_bytes())
    argv = ['vivado', '-mode', 'batch', '-source', str(out / 'source-snapshots' / TCL),
            '-log', 'vivado.log', '-journal', 'vivado.jou', '-tclargs', str(snapshots), str(out)]
    command = dict(argv=argv, cwd=str(out), log=str(out / 'command.log'))
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'command.log').open('w') as stream:
        result = subprocess.run(argv, cwd=out, stdout=stream, stderr=subprocess.STDOUT)
    command['returncode'] = result.returncode
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    require(result.returncode == 0 and 'CHUNKED_BANK_SYNTH_PASS' in (out / 'command.log').read_text(),
            f'Vivado incomplete; inspect {out / "command.log"}')
    with zipfile.ZipFile(out / 'ChunkedStorage.dcp') as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for text in ('<Part Name="xcvu47p-fsvh2892-2-e"', '<Top Name="ChunkedStorage"',
                     '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(text in metadata, 'native DCP identity: ' + text)
    utilization = (out / 'utilization.rpt').read_text()
    luts = int(re.search(r'\| CLB LUTs\*\s*\|\s*(\d+)\s*\|', utilization)[1])
    registers = int(re.search(r'\| CLB Registers\s*\|\s*(\d+)\s*\|', utilization)[1])
    names = ('ChunkedStorage.dcp', 'utilization.rpt', 'timing.rpt', 'vivado.log', 'vivado.jou',
             'command.log', 'command.json', 'native-functional.v')
    require(all((out / n).stat().st_size > 0 for n in names), 'missing native evidence')
    summary = dict(status='pass', backend='f2', original_root=str(ROOT), host=socket.gethostname(),
                   observed_utc=datetime.now(timezone.utc).isoformat(), physical_fpga_capture=False,
                   full_rocket_image_build=False, scope='native wide/deep bank component OOC synthesis only',
                   luts=luts, registers=registers, command=command,
                   sources={n: sha(out / 'source-snapshots' / n) for n in sources},
                   generated={n: sha(snapshots / n) for n in GENERATED}, artifacts={n: sha(out / n) for n in names})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
