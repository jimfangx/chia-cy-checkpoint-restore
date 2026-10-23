"""Native manager Vivado synthesis with immutable, per-execution inputs.

Fixture OOC synthesis only; never an AFI build or hardware capture receipt.
Source the local F2 HDK setup before invoking this command.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_checkpoint_top_vcs import GENERATED

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'native manager required')
    require(shutil.which('vivado') is not None, 'source native HDK setup first')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='top-vivado-', dir=base))
    snapshots = out / 'generated-snapshots'; snapshots.mkdir()
    for name in GENERATED:
        (snapshots / name).write_bytes((args.generated.resolve() / name).read_bytes())
    script = out / 'capture_top_synth.tcl'
    script.write_bytes((ROOT / 'tools/checkpoint_formats/capture_top_synth.tcl').read_bytes())
    argv = ['vivado', '-mode', 'batch', '-source', str(script), '-log', 'vivado.log',
            '-journal', 'vivado.jou', '-tclargs', str(snapshots), str(out)]
    command = dict(argv=argv, cwd=str(out), log=str(out / 'command.log'))
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'command.log').open('w') as stream:
        result = subprocess.run(argv, cwd=out, stdout=stream, stderr=subprocess.STDOUT)
    command['returncode'] = result.returncode
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    require(result.returncode == 0, f'Vivado failed; inspect {out / "command.log"}')
    require('CHECKPOINT_TOP_SYNTH_PASS' in (out / 'command.log').read_text(), 'synthesis incomplete')
    names = ('FPGATop.dcp', 'utilization.rpt', 'timing.rpt', 'vivado.log', 'vivado.jou',
             'command.log', 'command.json', 'fixture-clock-sink.v', 'capture_top_synth.tcl')
    require(all((out / n).is_file() and (out / n).stat().st_size > 0 for n in names), 'missing native evidence')
    summary = dict(status='pass', backend='f2', observed_utc=datetime.now(timezone.utc).isoformat(),
                   host=socket.gethostname(), original_root=str(ROOT), command=command,
                   physical_fpga_capture=False, full_rocket_image_build=False,
                   scope='native localhost fixture FPGATop out-of-context synthesis only',
                   generated={n: sha(snapshots / n) for n in GENERATED},
                   artifacts={n: sha(out / n) for n in names})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
