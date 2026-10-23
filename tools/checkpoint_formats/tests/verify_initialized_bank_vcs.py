"""EDA-only initialized storage clone/readout and unchanged-reference regression."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ('generated-bank-input.fir', 'generated-bank.fir', 'generated-bank.sv', 'reference.sv', 'reference.fir',
             'generated-bank-semantic.json', 'generated-bank-binding.json',
             'generated-bank-simulator.json', 'generated-bank-simulator-binding.json',
             'generated-bank-simulator.fir', 'source-annotations.json', 'translated-annotations.json',
             'left.hex', 'right.bin')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/InitializedStateBankSpec.scala',
           'tools/checkpoint_formats/tests/initialized_bank_tb.sv',
           'tools/checkpoint_formats/tests/verify_initialized_bank_vcs.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
            'run on EDA with vcs-env.sh sourced LAST')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='initialized-bank-', dir=base))
    hashes = {}
    for directory, source, names in (('source-snapshots', ROOT, SOURCES),
                                     ('generated-snapshots', args.generated.resolve(), GENERATED)):
        hashes[directory] = {}
        for name in names:
            dest = out / directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((source / name).read_bytes())
            hashes[directory][name] = sha(dest)
    snapshots = out / 'generated-snapshots'
    binding = json.loads((snapshots / 'generated-bank-binding.json').read_text())
    require(binding['reference_sha256'] == sha(snapshots / 'generated-bank-input.fir') and
            binding['instrumented_sha256'] == sha(snapshots / 'generated-bank.fir') and
            binding['manifest_sha256'] == sha(snapshots / 'generated-bank-semantic.json'), 'unbound storage')
    require(binding['annotation_translation']['source_sha256'] == sha(snapshots / 'source-annotations.json') and
            binding['annotation_translation']['translated_sha256'] == sha(snapshots / 'translated-annotations.json'),
            'unbound initialization or preservation annotations')
    entries = binding['state']
    require(len(entries) == 2 and {e['hierarchy'] for e in entries} ==
            {'InitializedStorage.a.ram', 'InitializedStorage.b.ram'}, 'incomplete repeated RAM ownership')
    sim = json.loads((snapshots / 'generated-bank-simulator-binding.json').read_text())
    require(sim['manifest_sha256'] == sha(snapshots / 'generated-bank-simulator.json') and
            sim['instrumented_sha256'] == sha(snapshots / 'generated-bank-simulator.fir') and
            sim['annotation_translation'] == binding['annotation_translation'] and
            not ({e['state_id'] for e in entries} & {e['state_id'] for e in sim['state']}),
            'simulator and semantic owners must remain independent')
    # The independent oracle is specified as values, not derived from the emitted
    # module names or memory filenames. Validate the exact transported init bytes.
    require([int(x, 16) for x in (snapshots / 'left.hex').read_text().split()] ==
            [17 + i * 29 for i in range(8)], 'hex image bytes changed')
    require([int(x, 2) for x in (snapshots / 'right.bin').read_text().split()] ==
            [401 - i * 31 for i in range(8)], 'binary image bytes changed')
    header = ['localparam integer ENTRY_COUNT=2;',
              'integer banks[0:1],slots[0:1],depths[0:1],kinds[0:1];', 'initial begin']
    for i, e in enumerate(entries):
        require((e['width'], e['depth']) == (9, 8), 'reshaped initialized RAM')
        kind = int(e['hierarchy'] == 'InitializedStorage.b.ram')
        header.append(f"banks[{i}]={e['bank']};slots[{i}]={e['slot']};depths[{i}]=8;kinds[{i}]={kind};")
    (out / 'initialized_bindings.svh').write_text('\n'.join(header + ['end']) + '\n')
    for name in ('left.hex', 'right.bin'):
        (out / name).write_bytes((snapshots / name).read_bytes())
    commands = []

    def run(argv, name):
        row = dict(argv=[str(a) for a in argv], cwd=str(out), log=str(out / name))
        commands.append(row)
        with (out / name).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == 0, f'command failed; inspect {out / name}')
        return (out / name).read_text()

    run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
         '-top', 'initialized_bank_tb', f'+incdir+{out}', f'-Mdir={out / "csrc"}', '-o', out / 'simv',
         snapshots / 'generated-bank.sv', snapshots / 'reference.sv',
         out / 'source-snapshots' / SOURCES[-2]], 'compile.log')
    log = run([out / 'simv', '-no_save'], 'run.log')
    match = re.search(r'INITIALIZED_BANK_PASS checks=(\d+) reads=(\d+) stalls=(\d+) functional_edges=(\d+) captures=(\d+) observations=(\d+)', log)
    require(match is not None and int(match[2]) == 69 and int(match[5]) == 4 and int(match[6]) > 500,
            'incomplete initialized state/continuation verification')
    words = [dict(zip(('cut', 'cycle', 'entry', 'address', 'data'), map(int, m)))
             for m in re.findall(r'WORD cut=(\d+) cycle=(\d+) entry=(\d+) address=(\d+) data=(\d+)',
                                 (out / 'captured-words.log').read_text())]
    require(len(words) == 64 and {w['cycle'] for w in words if w['cut'] == 0} == {0},
            'missing complete zero-edge initialized capture')
    require((out / 'initialized.vcd').stat().st_size > 1000, 'full debug waveform missing')
    summary = dict(status='pass', backend='eda', original_root=str(ROOT), host=socket.gethostname(),
                   observed_utc=datetime.now(timezone.utc).isoformat(), physical_fpga_capture=False,
                   scope='initialized repeated RAM annotation translation/readout; independent oracle and original RTL',
                   checks=int(match[1]), reads=int(match[2]), stalls=int(match[3]), functional_edges=int(match[4]),
                   captures=int(match[5]), observations=int(match[6]), hashes=hashes, commands=commands,
                   cuts=sorted({w['cycle'] for w in words}),
                   artifacts={p.name: sha(p) for p in out.iterdir() if p.is_file() and p.suffix in ('.log', '.vcd', '.svh', '.hex', '.bin')})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
