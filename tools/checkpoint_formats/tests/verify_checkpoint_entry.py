"""Production entry dispatch guards, native ASan/UBSan and actual VCS DPI.

Platform/registry/driver are observers, not generated-state restore evidence.
Run with env.sh, FireSim env.sh, then vcs-env.sh LAST.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == _toolchain.CXX, 'preserve VCS compiler setup')
    cc = ROOT/'sims/firesim/sim/midas/src/main/cc'
    tests = Path(__file__).resolve().parent
    header = tests/'checkpoint_entry_fixture.h'
    source = tests/'checkpoint_entry_fixture.cc'
    source_inputs = {}
    snapshots = out/'inputs'; snapshots.mkdir()
    for index, path in enumerate((Path(__file__), source, header, cc/'entry.cc',
                                 cc/'core/checkpoint_entry.h', ROOT/'tools/checkpoint_formats/fame_capture.cc')):
        path = path.resolve(); saved = snapshots/(str(index)+'-'+path.name)
        shutil.copyfile(path, saved)
        source_inputs[str(path)] = dict(snapshot=str(saved), sha256=hashlib.sha256(saved.read_bytes()).hexdigest())
    (out/'FireSim-generated.const.h').write_text(
        '#ifdef GET_METASIM_INTERFACE_CONFIG\nstatic TargetConfig conf_target;\n'
        '#undef GET_METASIM_INTERFACE_CONFIG\n#endif\n'
        '#ifdef GET_CORE_CONSTRUCTOR\nregistry.note_constructor();\n#endif\n')
    sv = out/'fixture.sv'
    sv.write_text('module checkpoint_entry_top;\n'
                  'import "DPI-C" context function int checkpoint_entry_fixture();\n'
                  'int status; initial begin status=checkpoint_entry_fixture();\n'
                  'if(status) $fatal(1,"entry returned failure"); $finish; end\nendmodule\n')
    common = ['-std=c++20', f'-I{cc}', f'-I{out}', f'-I{tests}', '-include', str(header)]
    binaries = []
    for backend in ('native', 'vcs'):
        for enabled, observer in ((False, False), (True, False), (False, True), (True, True)):
            directory = out/f'{backend}-{"enabled" if enabled else "default"}{"-observer" if observer else ""}'
            directory.mkdir(exist_ok=True)
            flags = [*common, *(['-DFS_CHECKPOINT_ENTRY'] if enabled else [])]
            binary = directory/'verify'
            if backend == 'native':
                run([os.environ['CXX'], *flags, *(['-DFIXTURE_UNOWNED_FAME_OBSERVER'] if observer else []),
                     '-g', '-fsanitize=address,undefined',
                     '-fno-omit-frame-pointer', '-no-pie', cc/'entry.cc', source, '-o', binary],
                    directory/'build.log')
                # entry's documented process-lifetime registry allocation is
                # intentional. Address/undefined behavior checks remain on.
                prefix = ['env', 'ASAN_OPTIONS=detect_leaks=0', binary]
            else:
                run([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '+vpi',
                     '-top', 'checkpoint_entry_top', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
                     '-CFLAGS', ' '.join([*flags, '-DVCS']), f'-Mdir={directory/"csrc"}',
                     '-o', binary, sv, cc/'entry.cc', source,
                     *([ROOT/'tools/checkpoint_formats/fame_capture.cc'] if observer else [])], directory/'build.log')
                prefix = [binary, '-no_save']
            binaries.append((backend, enabled, observer, directory, prefix))
    # The capability flag is an explicit link contract, not a weak fallback.
    missing = run([os.environ['CXX'], *common, '-DFS_CHECKPOINT_ENTRY', '-DFIXTURE_MISSING_FACTORY',
                   cc/'entry.cc', source, '-o', out/'missing-factory'], out/'missing-factory.log', expected=None)
    require('create_checkpoint_entry' in missing and not (out/'missing-factory').exists(),
            'missing enabled factory did not fail to link')
    results = []
    malformed = ['+fs-checkpoint', '+fs-restore', '+fs-checkpoint=', '+fs-restore=',
                 '+fs-checkpoint-preflight=1', '+fs-checkpoint-typo=x', '+fs-restore-typo=x']
    for backend, enabled, observer, directory, prefix in binaries:
        absent = directory/'must stay absent.fsckpt'
        existing = directory/'existing restore.fsckpt'; existing.write_bytes(b'unchanged durable input\n')
        capture = f'+fs-checkpoint={absent}'; restore = f'+fs-restore={existing}'
        periodic = [f'+fs-checkpoint-directory={directory/"absent-history"}', '+fs-checkpoint-interval=16',
                    '+fs-checkpoint-retention=2', '+fs-checkpoint-level=1']
        watchdog = [*periodic, '+fs-checkpoint-target-timeout-cycles=100', '+fs-checkpoint-capture-timeout-ms=100']
        cases = [('normal', [], 0, None, 'run'),
                 ('preflight', ['+fs-checkpoint-preflight'], 1, 'unsupported metasim runtime', 'preflight')]
        for i, option in enumerate(malformed):
            cases.append((f'malformed-{i}', [option], 1, 'Level-1 checkpoint', 'parse'))
        for i, options in enumerate(([capture, capture], [restore, restore], [capture, restore],
                                      ['+fs-checkpoint-preflight', restore], [restore, capture],
                                      ['+fs-checkpoint-preflight', '+fs-checkpoint-preflight'])):
            cases.append((f'conflict-{i}', options, 1, 'duplicate or conflicting', 'parse'))
        schedule = '+fs-checkpoint-operation='
        invalid_schedules = [[capture, schedule+value] for value in
                             ('', '0', '-1', '+1', '1x', '18446744073709551616')]
        invalid_schedules += [[capture, schedule+'3', schedule+'3'], [schedule+'3'],
                              [restore, schedule+'3'], ['+fs-checkpoint-preflight', schedule+'3'],
                              [capture, '+fs-checkpoint-operation'], [capture, '+fs-checkpoint-operation-typo=3']]
        for i, options in enumerate(invalid_schedules):
            cases.append((f'schedule-invalid-{i}', options, 1, 'checkpoint operation schedule', 'parse'))
        if enabled:
            cases += [('capture', [capture], 0, None, 'capture'), ('restore', [restore], 0, None, 'restore')]
            cases += [('schedule-before', [schedule+'3', capture], 0, None, 'capture'),
                      ('schedule-after', [capture, schedule+'18446744073709551615'], 0, None, 'capture')]
            for mode, error, phase in [
                ('deny', 'unsupported public durable', 'authorize'),
                ('authorize-error', 'fixture authorize failure', 'authorize'),
                ('factory-error', 'fixture factory failure', 'authorize'),
                ('null', 'has no capability', 'authorize'),
                ('widget', 'unsupported fixture widget', 'widget'),
                ('driver', 'unsupported checkpoint driver', 'driver'),
                ('empty-driver', 'unsupported empty checkpoint driver inventory', 'driver'),
                ('null-driver', 'unsupported checkpoint driver', 'driver'),
                ('prepare-error', 'fixture prepare failure', 'prepare'),
                ('wrong-restore', 'restore did not reserve fresh clocks', 'prepare')]:
                cases.append((mode, [f'+fixture-mode={mode}', restore], 1, error, phase))
            cases.append(('wrong-capture', ['+fixture-mode=wrong-capture', capture], 1,
                          'capture reserved restore clocks', 'prepare'))
        else:
            cases += [('capture', [capture], 1, 'no public durable checkpoint capability', 'authorize'),
                      ('restore', [restore], 1, 'no public durable checkpoint capability', 'authorize')]
        if observer:
            # The actual compiled backend denies Level 1 with no capture option
            # at all. Entry must not even call an otherwise accepting factory.
            cases = [('normal', [], 0, None, 'run')]
            for label, options in [('preflight', ['+fs-checkpoint-preflight']), ('capture', [capture]),
                                   ('restore', [restore]), ('periodic', periodic), ('watchdog', watchdog),
                                   ('restore-periodic', [restore, *periodic])]:
                cases.append(('compiled-observer-'+label, options, 1, 'unowned compiled observer state', 'parse'))
        for name in ('fame_capture', 'semantic_capture'):
            # Runtime plusargs exclude both observer implementations even if
            # the optional backend was not linked into this executable.
            cases.append((name+'-alone', ['+'+name+'=unused'], 0, None, 'run'))
            for value in ('unused', ''):
                option = '+'+name+'='+value
                for label, requests in [('preflight', ['+fs-checkpoint-preflight']), ('capture', [capture]),
                                        ('restore', [restore]), ('periodic', periodic), ('watchdog', watchdog),
                                        ('restore-periodic', [restore, *periodic])]:
                    for order, options in [('before', [option, *requests]), ('after', [*requests, option])]:
                        cases.append((name+'-'+('empty-' if not value else '')+label+'-'+order, options, 1,
                                      'unowned semantic capture observer state', 'parse'))
        if observer and enabled:
            # A linked capability also rejects private diagnostic capture
            # controls (which need no public request) at base construction.
            cases = [(label, options, 1, 'unowned compiled observer state', 'authorize')
                     if phase == 'run' else (label, options, code, error, phase)
                     for label, options, code, error, phase in cases]
            cases.append(('private-capture', ['+test-live-capture=unused'], 1,
                          'unowned compiled observer state', 'authorize'))
        for label, options, code, error, phase in cases:
            log = directory/f'{label}.log'
            text = run([*prefix, *options], log, directory, expected=code)
            if backend == 'vcs': require(_toolchain.VCS_VERSION in text, 'wrong VCS release')
            if error: require(error in text and 'FIXTURE_RETURN' not in text, 'failure returned to VCS/driver')
            if code or phase == 'restore': require('FIXTURE_RUN' not in text, 'rejected/reserved entry advanced target')
            if phase in ('parse', 'authorize'): require('FIXTURE_PLATFORM' not in text, 'early rejection constructed platform')
            if phase == 'parse': require('FIXTURE_FACTORY' not in text, 'parser failure invoked capability')
            if phase in ('widget', 'preflight'): require('FIXTURE_SIMULATION' not in text, 'unsupported widget initialized driver')
            if phase == 'driver': require('FIXTURE_PREPARE' not in text, 'unsupported driver reached prepare')
            if code == 0:
                require('FIXTURE_RETURN status=0' in text, 'success did not return')
                if phase in ('run', 'capture'): require('FIXTURE_RUN' in text, 'ordinary/capture run missing')
                if phase == 'restore': require('FS_CHECKPOINT_ENTRY_RESERVED before_run=1' in text, 'restore not reserved')
                if phase in ('capture', 'restore'):
                    require(f'path={existing if phase == "restore" else absent}\n' in text, 'opaque path was changed')
                    order = ['FIXTURE_AUTHORIZE', 'FIXTURE_PLATFORM', 'FIXTURE_PREFLIGHT',
                             'FIXTURE_SIMULATION', 'FIXTURE_DRIVER_INVENTORY', 'FIXTURE_PREPARE']
                    require([text.index(s) for s in order] == sorted(text.index(s) for s in order),
                            'public request validation/construction order changed')
            require(not absent.exists() and existing.read_bytes() == b'unchanged durable input\n',
                    'dispatch fixture published or modified a checkpoint')
            require(not (directory/'absent-history').exists(), 'rejected observer created periodic history')
            require('AddressSanitizer' not in text and 'runtime error:' not in text, 'sanitizer failure')
            results.append(dict(backend=backend, enabled=enabled, compiled_observer=observer,
                                case=label, argv=[str(a) for a in [*prefix, *options]], exit=code, log=str(log)))
    summary = dict(scope='production entry dispatch with observer platform/driver', cases=results,
                   native_sanitizers='ASan/UBSan (intentional process-lifetime registry excluded from leak checks)',
                   vcs_release=os.environ['VCS_HOME'], missing_factory_link_rejected=True,
                   production_durable_implementation_enabled=False,
                   level1_verified=False, level2_verified=False, source_inputs=source_inputs,
                   entry_sha256=hashlib.sha256((cc/'entry.cc').read_bytes()).hexdigest())
    for path, binding in source_inputs.items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == binding['sha256'], 'entry source changed during check')
    summary['artifact_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in out.rglob('*') if p.is_file()}
    (out/'summary.json').write_bytes(canonical(summary))
    print(f'PASS: {len(results)} native/VCS production entry dispatch cases; missing factory link rejection; {out/"summary.json"}')


if __name__ == '__main__':
    main()
