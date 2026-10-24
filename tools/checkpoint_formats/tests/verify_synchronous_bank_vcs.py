"""EDA-only original-RTL and independent-oracle synchronous bank regression."""
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
GENERATED = ('generated-bank.sv', 'reference.sv', 'generated-bank.fir', 'generated-bank-input.fir',
             'generated-bank-semantic.json', 'generated-bank-binding.json',
             'generated-bank-simulator.json', 'generated-bank-simulator-binding.json', 'generated-bank-simulator.fir')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/SynchronousStateBankSpec.scala',
           'tools/checkpoint_formats/tests/synchronous_bank_tb.sv',
           'tools/checkpoint_formats/tests/verify_synchronous_bank_vcs.py',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala')
ORACLE = {f'SyncStorage.{name}': (i, 9, 8) for i, name in
          enumerate(('oldMem', 'newMem', 'undefMem', 'rwOld', 'rwUndef'))}
ORACLE.update({f'SyncStorage.{name}': (i + 5, width, 1) for i, (name, width) in enumerate((
    ('oldMem_r_data', 9), ('newMem_r_addr', 3), ('undefMem_r_addr', 3),
    ('rwOld_p_rdata', 9), ('rwUndef_p_rdata', 9)))})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--default-read-first', action='store_true',
                        help='Verify backend-resolved undefined readers as old-data pipelines')
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
            'run on EDA with vcs-env.sh sourced LAST')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='synchronous-bank-', dir=base))
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
    entries = binding['state']
    oracle = dict(ORACLE)
    if args.default_read_first:
        del oracle['SyncStorage.undefMem_r_addr']
        oracle['SyncStorage.undefMem_r_data'] = (7, 9, 1)
        require('read-under-write => undefined' not in (snapshots/'generated-bank-input.fir').read_text(),
                'default memory policy was not resolved before inventory')
    require(len(entries) == 10 and {e['hierarchy'] for e in entries} == set(oracle), 'incomplete pipeline ownership')
    sim = json.loads((snapshots / 'generated-bank-simulator-binding.json').read_text())
    require(len(sim['state']) == 10 and sim['manifest_sha256'] == sha(snapshots / 'generated-bank-simulator.json')
            and sim['instrumented_sha256'] == sha(snapshots / 'generated-bank-simulator.fir') and
            sim['reference_sha256'] == binding['reference_sha256'] and
            {(e['hierarchy'], e['width'], e['depth']) for e in sim['state']} ==
            {(e['hierarchy'], e['width'], e['depth']) for e in entries} and
            not ({e['state_id'] for e in entries} & {e['state_id'] for e in sim['state']}),
            'simulator and semantic owners must remain independent')
    header = ['localparam integer ENTRY_COUNT=10;',
              'integer banks[0:9],slots[0:9],depths[0:9],kinds[0:9];', 'initial begin']
    for i, e in enumerate(entries):
        kind, width, depth = oracle[e['hierarchy']]
        require((e['width'], e['depth']) == (width, depth), 'reshaped owner')
        header.append(f"banks[{i}]={e['bank']};slots[{i}]={e['slot']};depths[{i}]={depth};kinds[{i}]={kind};")
    (out / 'synchronous_bindings.svh').write_text('\n'.join(header + ['end']) + '\n')
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
         *(['+define+DEFAULT_READ_FIRST'] if args.default_read_first else []),
         '-top', 'synchronous_bank_tb', f'+incdir+{out}', f'-Mdir={out / "csrc"}', '-o', out / 'simv',
         snapshots / 'generated-bank.sv', snapshots / 'reference.sv',
         out / 'source-snapshots' / 'tools/checkpoint_formats/tests/synchronous_bank_tb.sv'], 'compile.log')
    log = run([out / 'simv', '-no_save'], 'run.log')
    match = re.search(r'SYNCHRONOUS_BANK_PASS checks=(\d+) reads=(\d+) stalls=(\d+) functional_edges=(\d+) captures=(\d+) output_edges=(\d+)', log)
    require(match is not None and int(match[2]) == 454 and int(match[5]) == 10 and int(match[6]) > 2000,
            'incomplete synchronous state/continuation verification')
    require((out / 'synchronous.vcd').stat().st_size > 1000, 'full debug waveform missing')
    summary = dict(status='pass', backend='eda', original_root=str(ROOT), host=socket.gethostname(),
                   observed_utc=datetime.now(timezone.utc).isoformat(), physical_fpga_capture=False,
                   scope='five emitter synchronous reader/RW modes; independent public oracle and unchanged reference RTL',
                   default_read_first=args.default_read_first,
                   checks=int(match[1]), reads=int(match[2]), stalls=int(match[3]), functional_edges=int(match[4]),
                   captures=int(match[5]), output_edges=int(match[6]), hashes=hashes, commands=commands,
                   artifacts={p.name: sha(p) for p in out.iterdir() if p.is_file() and p.suffix in ('.log', '.vcd', '.svh')})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
