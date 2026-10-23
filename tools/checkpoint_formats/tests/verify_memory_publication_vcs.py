"""Production functional-memory preparation/sealing; synthetic component scope."""
from tools.checkpoint_formats import toolchain as _toolchain
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

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rocket-header', type=Path, required=True)
    a = parser.parse_args()
    require(a.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    header = a.rocket_header.resolve()
    require('.mem = AXI4Config{16, 34, 64}' in header.read_text() and
            '.mem_num_channels = 1' in header.read_text(), 'need exact Rocket memory geometry')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    sources = [TESTS / 'memory_publication.cc', CC / 'emul/mm.cc']
    sv = TESTS / 'memory_publication_tb.sv'
    inputs = [Path(__file__), TESTS / 'audit_memory_publication.py', sv, *sources,
              CC / 'emul/mm.h', CC / 'core/config.h', CC / 'core/checkpoint.h', header,
              ROOT / 'env.sh', ROOT / 'sims/firesim/env.sh', ROOT / 'automations/checkpoint_loop/vcs-env.sh']
    (out / 'sources').mkdir()
    bindings = []
    for f in sorted(set(inputs)):
        digest = file_sha(f)
        saved = out / 'sources' / digest
        if not saved.exists():
            shutil.copyfile(f, saved)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(saved)))
    (out / 'source-inputs.json').write_text(json.dumps(bindings, indent=2) + '\n')
    commands = []

    def execute(argv, name, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join(map(str, argv))]
        log = out / (name + '.log')
        run(command, log, cwd=out, expected=expected)
        result = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log))
        commands.append(result)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result

    includes = '-std=c++20 -I' + str(CC)
    execute([os.environ['CXX'], *shlex.split(includes), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, '-pthread', '-o', out / 'native'], 'native-build')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'memory_publication_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir=' + str(out / 'csrc'), '-CFLAGS', includes + ' -DMEMORY_PUBLICATION_DPI',
             '-LDFLAGS', '-pthread', '-o', out / 'simv', sv, *sources], 'vcs-build')
    cases = []
    modes = ('reference', 'restore', 'negative', 'fatal-unsealed', 'fatal-thread', 'fatal-destination',
             'fatal-recycled', 'fatal-consumed', 'fatal-stale', 'fatal-legacy')
    for backend in ('native', 'vcs-dpi'):
        for banks in (1, 4):
            for cut in range(4):
                reference = out / f'{backend}-{banks}-reference-{cut}'
                for mode in modes:
                    dest = reference if mode == 'reference' else out / f'{backend}-{banks}-{mode}-{cut}'
                    argv = ([out / 'native', mode, reference, dest, cut, banks] if backend == 'native' else
                            [out / 'simv', '-no_save', f'+mode={mode}', f'+source={reference}',
                             f'+destination={dest}', f'+cut={cut}', f'+banks={banks}'])
                    cases.append(dict(execute(argv, dest.name, 86 if mode.startswith('fatal-') else 0),
                                      backend=backend, banks=banks, mode=mode, cut=cut,
                                      destination=str(dest), reference=str(reference)))
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed ' + binding['path'])
    report = dict(status='passed', scope='production functional memory; synthetic AXI component',
                  level1_verified=False, level2_verified=False, rocket_header=str(header),
                  fixture_memory_bytes_per_bank=4096, exact_recipe_memory_channels=1,
                  additional_bank_group=4, cases=cases, commands=commands, source_inputs=bindings,
                  artifact_sha256={str(f): file_sha(f) for f in out.rglob('*') if f.is_file()})
    path = out / 'summary.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    from tools.checkpoint_formats.tests.audit_memory_publication import audit
    try:
        checked = audit(path)
    except Exception:
        report['status'] = 'failed'
        path.write_text(json.dumps(report, indent=2) + '\n')
        raise
    print(json.dumps(dict(summary=str(path), **checked), indent=2))


if __name__ == '__main__':
    main()
