"""Check production default HTIF device lifetime with sanitizers and native VCS.

Suspended stack teardown must release device allocations and duplicated file
descriptors. These resource checks grant no complete CPU checkpoint admission.
"""
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
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.fesvr_overlay import build_overlay, overlay_inputs
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf

CUTS = ('pristine', 'loader', 'poll', 'poll-partial', 'idle', 'bcd-pending',
        'syscall-pending', 'syscall-partial', 'syscall-returned', 'pass', 'fail')
SUCCESS = ('DEFAULT_DEVICE_LIFETIME instances=176 suspended=128 returned=32 '
           'leaked_descriptors=0 cpu_edges=0')


def audit(path):
    path = path.resolve(); report = json.loads(path.read_text()); out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and
            not report['level2_verified'], 'wrong device resource scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed device resource artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed device resource artifact ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed resource source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    require((out/'polling.elf').read_bytes() == polling_elf(), 'changed actual device resource ELF')
    for backend in ('native-sanitizer', 'vcs-dpi'):
        text = (out/(backend+'.log')).read_text()
        require(SUCCESS in text and not any(marker in text for marker in
                ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')),
                'device resource lifetime failed ' + backend)
        for cut in CUTS:
            require('DEVICE_CUT cut='+cut+' repetitions=16 unchanged_descriptors=1' in text,
                    'missing suspended device cut ' + cut)
    if report['negative_control']:
        text = Path(report['negative_control']['log']).read_text()
        require('DEVICE_RESOURCE_LEAK cut=poll repetition=0 leaked_descriptors=3' in text and
                text.rstrip().endswith('exit=3'), 'original resource leak not reproduced')
    for command in report['commands']:
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT),
                'wrong device resource command environment')
        require(Path(command['log']).read_text().rstrip().endswith('exit='+str(command['expected_exit'])),
                'unbound device resource command result')
    return dict(status='passed', backends=2, instances=352, suspended=256, returned=64,
                exact_descriptor_readbacks=352, cuts=list(CUTS),
                original_leak_reproduced=bool(report['negative_control']),
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--negative-control-source', type=Path,
                        help='Retained original firesim_tsi.cc with its original header alongside')
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env.sh LAST')
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),
            'diagnostics must be under runs')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    fixture, sv = TESTS/'tsi_device_lifetime.cc', TESTS/'tsi_device_lifetime_tb.sv'
    sources = [fixture, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, Path(__file__), *overlay_inputs(), FESVR/'lib/libfesvr.a',
              TESTS/'verify_tsi_host_control_fesvr_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')),
              *sorted((FESVR/'include/fesvr').glob('*.h')),
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    if args.negative_control_source:
        original = args.negative_control_source.resolve()
        require(original.is_relative_to(ROOT/'automations/checkpoint_loop/runs') and original.is_file() and
                original.with_suffix('.h').is_file(), 'need retained original source/header under runs')
        inputs += [original, original.with_suffix('.h')]
    snapshots = out/'sources'; snapshots.mkdir(); bindings = []
    for source in dict.fromkeys(inputs):
        digest = file_sha(source); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(source, snapshot)
        bindings.append(dict(path=str(source), sha256=digest, snapshot=str(snapshot)))
    commands = []

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join(map(str, argv))]
        text = run(command, log, cwd=ROOT, expected=expected)
        result = dict(cwd='.', argv=command, log=str(log), expected_exit=expected)
        commands.append(result); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return text

    library = build_overlay(out, execute)
    elf = out/'polling.elf'; elf.write_bytes(polling_elf())
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    negative = None
    if args.negative_control_source:
        # Both translation units must use the original class layout. Merely
        # replacing the .cc while compiling the fixture with the new header
        # would violate the ODR and would not be a meaningful leak control.
        control_headers = out/'original-headers'
        (control_headers/'fesvr').mkdir(parents=True)
        shutil.copyfile(original, control_headers/'fesvr/firesim_tsi.cc')
        shutil.copyfile(original.with_suffix('.h'), control_headers/'fesvr/firesim_tsi.h')
        control = out/'original-native'
        execute([os.environ['CXX'], '-I'+str(control_headers), '-I'+str(STUBS/'fesvr'),
                 *shlex.split(include), '-g', fixture, control_headers/'fesvr/firesim_tsi.cc', *sources[2:],
                 library, '-lpthread', '-o', control], out/'original-build.log')
        execute([control, elf, out/'original'], out/'original.log', expected=3)
        negative = commands[-1]
    native, simv = out/'native', out/'simv'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    execute([native, elf, out/'native-cuts'], out/'native-sanitizer.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tsi_device_lifetime_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_DEVICE_LIFETIME_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
             '-o', simv, sv, *sources], out/'vcs-build.log')
    execute([simv, '-no_save', '+source='+str(elf), '+destination='+str(out/'vcs-dpi')], out/'vcs-dpi.log')
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during device resource check')
    report = dict(status='passed', scope='process-local default device lifetime; semantic owners remain pending',
                  commands=commands, source_inputs=bindings, negative_control=negative,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(audit(path), summary=str(path)), indent=2))


if __name__ == '__main__':
    main()
