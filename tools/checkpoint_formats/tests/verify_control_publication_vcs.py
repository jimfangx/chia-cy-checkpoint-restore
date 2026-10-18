"""Prepared production scheduler/run-loop continuations; component scope."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.audit_control_publication import cuts, MODES

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    sources = [TESTS / 'control_publication.cc', CC / 'core/systematic_scheduler.cc', CC / 'core/bridge_run_loop.cc']
    sv = TESTS / 'control_publication_tb.sv'
    inputs = [Path(__file__), TESTS / 'audit_control_publication.py', sv, *sources,
              *[CC / ('core/' + n + '.h') for n in ('checkpoint', 'checkpoint_publication', 'systematic_scheduler', 'bridge_run_loop')],
              ROOT / 'env.sh', ROOT / 'sims/firesim/env.sh', ROOT / 'automations/checkpoint_loop/vcs-env.sh']
    (out / 'sources').mkdir()
    bindings = []
    for f in sorted(set(inputs)):
        h = file_sha(f); saved = out / 'sources' / h
        if not saved.exists():
            shutil.copyfile(f, saved)
        bindings.append(dict(path=str(f), sha256=h, snapshot=str(saved)))
    (out / 'source-inputs.json').write_text(json.dumps(bindings, indent=2) + '\n')
    commands, cases = [], []

    def execute(argv, name, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join(map(str, argv))]
        log = out / (name + '.log')
        run(command, log, cwd=out, expected=expected)
        result = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log))
        commands.append(result)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result

    flags = '-std=c++20 -I' + str(CC)
    execute([os.environ['CXX'], *shlex.split(flags), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, '-pthread', '-o', out / 'native'], 'native-build')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'control_publication_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir=' + str(out / 'csrc'), '-CFLAGS', flags + ' -DCONTROL_PUBLICATION_DPI',
             '-LDFLAGS', '-pthread', '-o', out / 'simv', sv, *sources], 'vcs-build')
    for backend in ('native', 'vcs-dpi'):
        for scenario in range(2):
            reference = out / f'{backend}-{scenario}-reference'
            for mode, cut in [('reference', 0)] + [(m, c) for c in cuts(scenario) for m in MODES]:
                dest = reference if mode == 'reference' else out / f'{backend}-{scenario}-{mode}-{cut}'
                argv = ([out / 'native', mode, reference, dest, scenario, cut] if backend == 'native' else
                        [out / 'simv', '-no_save', f'+mode={mode}', f'+source={reference}',
                         f'+destination={dest}', f'+scenario={scenario}', f'+cut={cut}'])
                cases.append(dict(execute(argv, dest.name, 86 if mode.startswith('fatal-') else 0), backend=backend,
                                  scenario=scenario, mode=mode, cut=cut, destination=str(dest), reference=str(reference)))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'control source changed ' + b['path'])
    r = dict(status='passed',scope='production scheduler/bridge-loop; synthetic services',CPU_level1_verified=False,
             cases=cases,commands=commands,source_inputs=bindings,
             artifact_sha256={str(f): file_sha(f) for f in out.rglob('*') if f.is_file()})
    report = out / 'summary.json'
    report.write_text(json.dumps(r, indent=2) + '\n')
    from tools.checkpoint_formats.tests.audit_control_publication import audit
    try:
        checked = audit(report)
    except Exception:
        r['status'] = 'failed'; report.write_text(json.dumps(r, indent=2) + '\n'); raise
    print(json.dumps(dict(summary=str(report), **checked), indent=2))


if __name__ == '__main__':
    main()
