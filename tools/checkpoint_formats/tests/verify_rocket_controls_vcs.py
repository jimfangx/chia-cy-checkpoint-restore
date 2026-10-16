"""Rebuild the exact Rocket recipe and run complete four-hart controls.

Each invocation owns a new retained directory, executable, logs and traces.
These are uninterrupted workload controls, not CPU checkpoint acceptance.
Every VCS subprocess independently sources both environments and vcs-env last.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.cpu_native import VCS_HOME, record_build
from tools.checkpoint_formats.cpu_recipe import ROOT, RECIPES, native_build_command, recipe_settings
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.simulator import check_generated_rtl
from tools.checkpoint_formats.native_regressions import source_inputs

ENVIRONMENT = ('source env.sh && source sims/firesim/env.sh && '
               'source automations/checkpoint_loop/vcs-env.sh && ')
LABEL_KEYS = ('hart_phases', 'completed_harts', 'failure_stores',
              'tohost_stores', 'workload_retirements')


def execute(command, destination, name):
    log = destination / (name + '.log')
    with log.open('x') as stream:
        stream.write(json.dumps(command) + '\n')
        stream.flush()
        process = subprocess.Popen(command['argv'], cwd=ROOT / command['cwd'],
                                   stdout=stream, stderr=subprocess.STDOUT)
        stream.write('fresh_process_pid=' + str(process.pid) + '\n')
        stream.flush()
        code = process.wait()
        stream.write('exit=' + str(code) + '\n')
    result = dict(command, purpose=name, returncode=code, log=str(log), pid=process.pid)
    (destination / (name + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
    require(code == 0, name + ' failed: ' + str(log))
    return result


def control(binary, workload, reference, reference_audit, out, buffered, host_audit_cycles=None):
    name = 'rocket-buffered' if buffered else 'rocket'
    runtime = out / (name + '-runtime')
    runtime.mkdir()
    elf = Path(json.loads((workload / 'summary.json').read_text())['builds']['rocket-quad']['elf'])
    argv = [str(binary), '+permissive', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
            '+memsize=17179869184', '+max-cycles=5000000', '+fesvr-step-size=128',
            '+blkdev-in-mem0=128', '+mm_useHardwareDefaultRuntimeSettings_0',
            '+tracefile=' + str(runtime / 'TRACEFILE')]
    if host_audit_cycles is not None:
        argv += ['+tsi-host-audit=' + str(runtime / 'tsi-host-audit'),
                 '+tsi-host-audit-cycles=' + host_audit_cycles]
    if buffered:
        (runtime / 'input.bin').write_bytes(b'')
        argv += ['+tracerv-checkpoint-buffered', '+heartbeat-checkpoint-buffered',
                 '+heartbeat-output=' + str(runtime / 'heartbeat.csv'),
                 '+uart-checkpoint-file0', '+uart-in0=' + str(runtime / 'input.bin'),
                 '+uart-out0=' + str(runtime / 'output.bin')]
    argv += ['+permissive-off', str(elf)]
    command = dict(cwd='.', argv=['bash', '-lc', ENVIRONMENT + 'cd ' +
                                 shlex.quote(str(runtime)) + ' && ' + shlex.join(argv)])
    (runtime / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    run = execute(command, out, name + '-workload')
    (runtime / 'exit.json').write_text(json.dumps(dict(returncode=0, checkpoint_acceptance=False)) + '\n')
    # Retain one actual process log; the workload auditor resolves the link.
    (runtime / 'native-vcs.log').symlink_to(Path(run['log']))
    audit_path = out / (name + '-workload-audit.json')
    audit = execute(dict(cwd='.', argv=['python', '-m',
                    'tools.checkpoint_formats.tests.audit_rocket_baseline',
                    '--runtime', str(runtime), '--workload', str(workload),
                    '--out', str(audit_path)]), out, name + '-workload-audit')
    current = json.loads(audit_path.read_text())
    original = json.loads(reference_audit.read_text())
    for key in LABEL_KEYS:
        require(current[key] == original[key], 'changed CPU control target labels: ' + key)
    comparisons = []
    for hart in range(4):
        actual, expected = runtime / f'TRACEFILE-C{hart}', reference / f'TRACEFILE-C{hart}'
        require(actual.stat().st_size == expected.stat().st_size and file_sha(actual) == file_sha(expected),
                'changed complete four-hart instruction trace: ' + str(hart))
        comparisons.append(dict(current=str(actual), reference=str(expected),
                                bytes=actual.stat().st_size, sha256=file_sha(actual)))
    if buffered:
        require((runtime / 'output.bin').read_bytes() == b'', 'unexpected workload UART output')
        rows = (runtime / 'heartbeat.csv').read_text().splitlines()
        require(rows and rows[0] == 'Target Cycle (fastest), Seconds Since Start',
                'missing complete buffered heartbeat log')
        cycles = [int(row.split(',')[0]) for row in rows[1:]]
        require(all(a < b for a, b in zip([0] + cycles, cycles)), 'invalid heartbeat target progress')
    matches = re.findall(r'\*\*\* PASSED \*\*\* after (\d+) cycles', Path(run['log']).read_text())
    require(len(matches) == 1, 'missing/ambiguous CPU workload completion')
    result = dict(status='passed', scope='complete uninterrupted four-hart CPU control',
                  mode=name, end_target_count=int(matches[0]), comparisons=comparisons,
                  native_binary=str(binary), native_binary_sha256=file_sha(binary),
                  workload_sha256=file_sha(elf), full_backing_memory_bytes=17179869184,
                  tracerv_checkpoint_buffered=buffered,
                  host_audit_cycles=host_audit_cycles,
                  level1_verified=False, level2_verified=False)
    (out / (name + '-control-summary.json')).write_text(json.dumps(result, indent=2) + '\n')
    return [run, audit], result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seed-build', type=Path)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--reference-runtime', type=Path, required=True)
    parser.add_argument('--reference-audit', type=Path, required=True)
    parser.add_argument('--host-audit-cycles', help='Optional comma-separated master-credit diagnostic cuts')
    parser.add_argument('--htif-source', type=Path, help='Opt-in exact-header lifecycle provider')
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == VCS_HOME, 'source vcs-env.sh LAST')
    destination = args.out.resolve()
    require(destination.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
            'CPU diagnostics must be under checkpoint runs')
    workload, reference, reference_audit = (p.resolve() for p in
                                           (args.workload, args.reference_runtime, args.reference_audit))
    workload_report = json.loads((workload / 'summary.json').read_text())
    elf = Path(workload_report['builds']['rocket-quad']['elf'])
    require(workload_report['status'] == 'passed' and workload_report['harts'] == 4 and
            file_sha(elf) == workload_report['builds']['rocket-quad']['sha256'],
            'missing or incompatible complete four-hart workload')
    require(json.loads(reference_audit.read_text())['status'] == 'passed' and
            all((reference / f'TRACEFILE-C{hart}').is_file() for hart in range(4)),
            'missing complete independent uninterrupted reference')
    recipe = recipe_settings(RECIPES['Rocket'])
    destination.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=destination))
    (out / 'invocation.json').write_text(json.dumps(dict(recipe=recipe, args=vars(args)),
                                                    default=str, indent=2) + '\n')
    # latest selects a concrete invocation, never redirects earlier artifacts.
    (destination / 'latest.json').write_text(json.dumps(dict(artifact_root=str(out))) + '\n')
    if args.seed_build:
        seed = args.seed_build.resolve()
        require(seed.is_dir() and seed.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
                'seed must be an existing diagnostic build')
        subprocess.run(['cp', '-a', '--reflink=auto', str(seed), str(out / 'build')], check=True)
    # Freeze maintained native sources BEFORE compilation, not just after it.
    # Generated artifacts are subsequently bound by record_build.
    inputs = source_inputs(ROOT) | {Path(recipe['recipe_file'])}
    for directory in ('generators/firechip/bridgestubs/src/main', 'generators/firechip/chip/src/main',
                      'generators/testchipip/src/main/resources/testchipip/csrc'):
        inputs.update(p for p in (ROOT / directory).rglob('*') if p.is_file() and
                      p.suffix in ('.cc', '.h', '.inc', '.mk'))
    if args.htif_source:
        inputs.update((args.htif_source.resolve(), args.htif_source.resolve().with_suffix('.h')))
    snapshots = out / 'source-snapshots'
    snapshots.mkdir()
    bindings = []
    for path in sorted(inputs):
        digest = file_sha(path)
        snapshot = snapshots / digest
        if not snapshot.exists():
            shutil.copyfile(path, snapshot)
        require(file_sha(snapshot) == file_sha(path) == digest, 'source changed before CPU build')
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    (out / 'pre-build-inputs.json').write_text(json.dumps(dict(files=bindings), indent=2) + '\n')
    commands = [execute(native_build_command(recipe, out / 'build', 'vcs', htif_source=args.htif_source), out, 'rocket-vcs-build')]
    builds = list((out / 'build/f2').iterdir())
    require(len(builds) == 1, 'ambiguous exact-recipe native build directory')
    build = builds[0]
    identity = record_build(recipe, build, out / 'rocket-vcs-build.log', out / 'rocket-build-identity.json')
    require(identity['htif_lifecycle_provider_linked'] == bool(args.htif_source),
            'CPU build did not link the selected HTIF variant')
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during CPU build')
    base = build / 'FireSim-generated'
    manifest = json.loads(base.with_suffix('.simulator-state.json').read_text())
    bufgce = (ROOT / 'sims/firesim/sim/midas/src/main/verilog/BUFGCE.v').read_text()
    check_generated_rtl(manifest, base.with_suffix('.simulator-reference.fir').read_text(),
                        base.with_suffix('.sv').read_text() + bufgce, bufgce,
                        plusarg_model=(build / 'plusarg_reader.v').read_text())
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(control, build / 'FireSim', workload, reference, reference_audit, out, buffered, args.host_audit_cycles)
                for buffered in (False, True)]
        results = [job.result() for job in jobs]
    for ran, _ in results:
        commands += ran
    # Verify all recorded inputs again after both complete native processes.
    for path, digest in identity['sources_sha256'].items():
        require(file_sha(path) == digest, 'native input changed while controls ran: ' + path)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during CPU controls')
    summary = dict(status='passed', scope='exact recipe rebuild and two complete four-hart controls',
                   artifact_root=str(out), recipe=recipe, commands=commands,
                   controls=[result for _, result in results],
                   input_hashes={str(Path(__file__).resolve()): file_sha(__file__),
                                 str(workload / 'summary.json'): file_sha(workload / 'summary.json'),
                                 str(reference_audit): file_sha(reference_audit)},
                   pre_build_inputs=str(out / 'pre-build-inputs.json'),
                   pre_build_inputs_sha256=file_sha(out / 'pre-build-inputs.json'),
                   level1_verified=False, level2_verified=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', summary=str(out / 'summary.json'),
                          level1_verified=False, level2_verified=False)))


if __name__ == '__main__':
    main()
