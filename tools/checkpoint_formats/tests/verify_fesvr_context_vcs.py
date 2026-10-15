"""Check FESVR stack lifetime with allocation accounting, sanitizers and VCS.

This owns process-local context resources; it does not restore CPU checkpoints.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.fesvr_overlay import build_overlay, overlay_inputs, INSTALLED
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

TESTS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env.sh LAST')
    destination = args.out.resolve()
    require(destination.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'diagnostics must be under runs')
    destination.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=destination))
    sources = [Path(__file__), *overlay_inputs(), TESTS/'fesvr_context_lifetime.cc',
               TESTS/'fesvr_context_lifetime_tb.sv', INSTALLED/'include/fesvr/context.h',
               INSTALLED/'lib/libfesvr.a', ROOT/'env.sh', ROOT/'sims/firesim/env.sh',
               ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'source-snapshots'; snapshots.mkdir()
    bindings = []
    for source in sources:
        digest = file_sha(source); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(source, snapshot)
        bindings.append(dict(path=str(source), sha256=digest, snapshot=str(snapshot)))
    commands = []

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + 'ulimit -c 0 && ' + shlex.join(map(str, argv))]
        text = run(command, log, cwd=ROOT, expected=expected)
        commands.append(dict(cwd='.', argv=command, log=str(log), expected_exit=expected))
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return text

    library = build_overlay(out, execute)
    fixture = TESTS/'fesvr_context_lifetime.cc'
    common = [os.environ['CXX'], '-std=c++17', '-g', '-fno-omit-frame-pointer', '-no-pie',
              '-fsanitize=address,undefined', '-I'+str(INSTALLED/'include'), fixture]
    native, original, simv = out/'native', out/'installed-native', out/'simv'
    execute([*common, library, '-pthread', '-o', native], out/'native-build.log')
    execute([*common, INSTALLED/'lib/libfesvr.a', '-pthread', '-o', original], out/'installed-build.log')
    control = execute([original, 'stack-leak'], out/'installed-negative.log', expected=None)
    require('STACK_LIFETIME allocated=2 released=0 live=2' in control,
            'original installed context failed for an unexpected reason')
    text = execute([native, 'checks'], out/'native.log')
    expected = 'CONTEXT suspended=128 returned=128 switches=1018 allocated=278 released=278 live=0'
    require(expected in text and not any(x in text for x in
            ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'native lifetime accounting failed')
    include = '-std=c++17 -DFESVR_CONTEXT_DPI -I'+str(INSTALLED/'include')
    # Extract only the audited context member; VCS must not select libriscv.so.
    import subprocess
    obj = out/'context.o'
    obj.write_bytes(subprocess.check_output(['ar', 'p', library, 'context.o']))
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog',
             '-timescale=1ns/1ps', '-top', 'fesvr_context_lifetime_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir='+str(out/'csrc'), '-CFLAGS', include, '-LDFLAGS', '-pthread',
             '-o', simv, TESTS/'fesvr_context_lifetime_tb.sv', fixture, obj], out/'vcs-build.log')
    vcs_text = execute([simv, '-no_save', '+mode=checks'], out/'vcs.log')
    require(expected in vcs_text, 'VCS complete lifetime accounting failed')
    for mode, message in [('active-destroy', 'destroying the active context'),
                          ('active-exit', 'thread exit while a child is active'),
                          ('creator-destroy', 'destroying the creator of a suspended context')]:
        for backend, argv in [('native', [native, mode]), ('vcs', [simv, '-no_save', '+mode='+mode])]:
            output = execute(argv, out/(backend+'-'+mode+'.log'), expected=None)
            require('FESVR context lifetime: '+message in output, 'lifetime violation was not explicitly rejected')
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during lifetime verification')
    report = dict(status='passed', scope='process-local stack resources; no CPU checkpoint admission',
                  native_sanitizer_passed=True, allocation_accounting_per_backend=dict(
                      suspended=128, returned=128, switches=1018, allocated=278, released=278, live=0),
                  retained_worker_stack_release=True,
                  invalid_lifetime_death_checks=6, installed_leak_negative_control=True,
                  commands=commands, source_inputs=bindings,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status='passed', summary=str(out/'summary.json'),
                         level1_verified=False, level2_verified=False), indent=2))


if __name__ == '__main__':
    main()
