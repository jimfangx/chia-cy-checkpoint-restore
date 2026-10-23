"""Prepared mutable-scalar production widgets; component scope."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from tools.checkpoint_formats.tests.audit_scalar_publication import FATAL

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    sources = [TESTS / 'scalar_publication.cc', CC / 'core/widget.cc',
               CC / 'core/stream_engine.cc', *[CC / ('bridges/' + n + '.cc') for n in ('peek_poke', 'cpu_managed_stream')]]
    sv = TESTS / 'scalar_publication_tb.sv'
    inputs = [Path(__file__), TESTS / 'audit_scalar_publication.py', sv, *sources,
              *[CC / ('core/' + n + '.h') for n in ('checkpoint', 'checkpoint_publication', 'stream_engine', 'widget_checkpoint', 'widget', 'simif', 'config', 'bridge_driver', 'timing')],
              *[CC / ('bridges/' + n + '.h') for n in ('peek_poke', 'cpu_managed_stream')],
              TESTS / 'verify_semantic_vcs.py', TESTS / 'verify_loadmem_read_checkpoint_vcs.py',
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
        return result

    flags = '-std=c++20 -I' + str(CC)
    commands.append(execute([os.environ['CXX'], *shlex.split(flags), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, '-pthread', '-lgmp', '-o', out / 'native'], 'native-build'))
    commands.append(execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'scalar_publication_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir=' + str(out / 'csrc'), '-CFLAGS', flags + ' -DSCALAR_PUBLICATION_DPI',
             '-LDFLAGS', '-pthread -Wl,--no-as-needed -lgmp -Wl,--as-needed', '-o', out / 'simv', sv, *sources], 'vcs-build'))
    def case(backend, mode, cut):
        reference = out / f'{backend}-reference'
        dest = reference if mode == 'reference' else out / f'{backend}-{mode}-{cut}'
        argv = ([out / 'native', mode, reference, dest, cut] if backend == 'native' else
                [out / 'simv', '-no_save', f'+mode={mode}', f'+source={reference}',
                 f'+destination={dest}', f'+cut={cut}'])
        return dict(execute(argv, dest.name, 86 if mode.startswith('fatal-') else 0), backend=backend,
                    mode=mode, cut=cut, destination=str(dest), reference=str(reference))
    for backend in ('native', 'vcs-dpi'):
        cases.append(case(backend, 'reference', 0))
        modes = [(m, c) for c in range(20) for m in ('restore', 'negative')]
        modes += [('fatal-'+m, c) for m in FATAL for c in range(2)]
        with ThreadPoolExecutor(max_workers=3) as executor:
            cases.extend(executor.map(lambda mc: case(backend, *mc), modes))
    commands.extend({k: c[k] for k in ('argv', 'cwd', 'log')} for c in cases)
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'scalar source changed ' + b['path'])
    r = dict(status='passed',scope='two mutable-scalar host owners; fixture MMIO/DMA/clock',CPU_level1_verified=False,
             cases=cases,commands=commands,source_inputs=bindings,
             artifact_sha256={str(f): file_sha(f) for f in out.rglob('*') if f.is_file()})
    report = out / 'summary.json'
    report.write_text(json.dumps(r, indent=2) + '\n')
    from tools.checkpoint_formats.tests.audit_scalar_publication import audit
    try:
        checked = audit(report)
    except Exception:
        r['status'] = 'failed'; report.write_text(json.dumps(r, indent=2) + '\n'); raise
    print(json.dumps(dict(summary=str(report), **checked), indent=2))


if __name__ == '__main__':
    main()
