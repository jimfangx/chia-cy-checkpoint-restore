"""Fresh native/VCS simulation_t base lifecycle publication; component scope."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_simulation_checkpoint_vcs import CC, TESTS, oracle
from tools.checkpoint_formats.tests.audit_base_publication import audit, FATAL, ENVIRONMENT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--legacy', action='store_true')
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    sources = [TESTS / 'simulation_checkpoint.cc', *[CC / p for p in (
        'core/simulation.cc', 'core/widget_registry.cc', 'core/widget.cc',
        'core/stream_engine.cc', 'core/bridge_driver.cc', 'bridges/master.cc',
        'bridges/clock.cc', 'bridges/loadmem.cc')]]
    inputs = [*sources, TESTS / 'simulation_checkpoint_tb.sv', Path(__file__),
              TESTS / 'audit_base_publication.py', TESTS / 'verify_simulation_checkpoint_vcs.py',
              TESTS / 'verify_semantic_vcs.py', *sorted((CC / 'core').glob('*.h')),
              *sorted((CC / 'bridges').glob('*.h')), ROOT / 'env.sh', ROOT / 'sims/firesim/env.sh',
              ROOT / 'automations/checkpoint_loop/vcs-env.sh']
    (out / 'sources').mkdir()
    bindings = []
    for path in inputs:
        digest = file_sha(path); saved = out / 'sources' / digest
        if not saved.exists(): shutil.copyfile(path, saved)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(saved)))
    commands = []

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join(map(str, argv))]
        log.parent.mkdir(parents=True, exist_ok=True)
        result = run(command, log, cwd=out, expected=expected)
        commands.append(dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log),
                             expected_exit=expected, pid=int(re.search(r'fresh_process_pid=(\d+)', result)[1])))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return result

    flags = '-std=c++17 -I' + str(CC)
    if not args.legacy: flags += ' -DSIMULATION_PREPARED_PUBLICATION'
    native, simv = out / 'native', out / 'simv'
    execute([os.environ['CXX'], *shlex.split(flags), '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
             '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, '-pthread', '-lgmp', '-o', native], out / 'native-build.log')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'simulation_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir='+str(out / 'csrc'), '-CFLAGS', flags+' -DSIMULATION_CHECKPOINT_DPI',
             '-LDFLAGS', '-pthread -Wl,--no-as-needed -lgmp', '-o', simv,
             TESTS / 'simulation_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend; base.mkdir()
        def invoke(source, destination, restore, cut, scenario, expected=0):
            argv = [native, source, destination, int(restore), cut, scenario] if backend == 'native-sanitized' else [
                simv, '-no_save', '+source='+str(source), '+outdir='+str(destination),
                '+restore='+str(int(restore)), '+cut='+str(cut), '+scenario='+str(scenario)]
            return execute(argv, destination / 'run.log', expected)
        for scenario in range(3):
            reference = base / str(scenario) / 'reference'
            invoke(reference, reference, False, 1, scenario)
            for cut in range(1, 5):
                invoke(reference, reference.parent / ('restore-'+str(cut)), True, cut, scenario)
        execute([native, 'negative'] if backend == 'native-sanitized' else [simv, '-no_save', '+negative'],
                base / 'negative.log')
        for i, bad in enumerate((b'', oracle(1)[:-1], oracle(1)+b'\0', b'\0'*len(oracle(1)))):
            case = base / ('malformed-'+str(i)); case.mkdir()
            (case / 'cut-1.owner').write_bytes(bad)
            invoke(case, case, True, 1, 0, 1)
        for cut in (3, 4):
            case = base / ('done-corruption-'+str(cut)); case.mkdir()
            bad = bytearray(oracle(cut)); bad[-24] ^= 1
            (case / ('cut-'+str(cut)+'.owner')).write_bytes(bad)
            invoke(case, case, True, cut, 0, 1)
        if not args.legacy:
            execute([native, 'publication-negative'] if backend == 'native-sanitized' else
                    [simv, '-no_save', '+publication-negative'], base / 'publication-negative.log')
            for mode in (*FATAL, 'returned'):
                execute([native, 'publication-fatal', mode] if backend == 'native-sanitized' else
                        [simv, '-no_save', '+publication-fatal='+mode],
                        base / ('publication-'+mode+'.log'), 88 if mode == 'returned' else 86)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during execution')
    report = dict(status='passed', scope='simulation_t base lifecycle component; MMIO/driver/bridge fixtures',
                  prepared=not args.legacy, CPU_level1_verified=False, CPU_level2_verified=False,
                  source_inputs=bindings, commands=commands,
                  artifact_sha256={str(p): file_sha(p) for p in out.rglob('*') if p.is_file()})
    summary = out / 'summary.json'; summary.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(summary), **audit(summary)), indent=2))


if __name__ == '__main__':
    main()
