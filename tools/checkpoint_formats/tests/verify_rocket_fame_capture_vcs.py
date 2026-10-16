"""Build exact Rocket recipe, capture actual semantic windows, audit full workload.

Run after sourcing both environments and vcs-env.sh LAST. Each invocation owns
a new metasim build and full 16-GiB four-hart run; no CPU Level-1 admission.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.cpu_native import record_build
from tools.checkpoint_formats.cpu_recipe import RECIPES, ROOT, native_build_command, recipe_settings
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.fame_event import audit_event_boundary, prepare_monitor
from tools.checkpoint_formats.native_regressions import source_inputs
from tools.checkpoint_formats.tests.verify_rocket_controls_vcs import ENVIRONMENT, LABEL_KEYS, execute
from tools.checkpoint_formats.tests.verify_semantic_fame_map_vcs import read_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--reference-runtime', type=Path, required=True)
    parser.add_argument('--reference-audit', type=Path, required=True)
    parser.add_argument('--cuts', default='100,700000,900000,3250000')
    parser.add_argument('--events', type=int, default=64)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'capture diagnostics belong under runs')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    builds = list((args.seed_build.resolve() / 'f2').iterdir())
    require(len(builds) == 1, 'ambiguous exact Rocket seed build')
    paths, text, docs, _ = read_inputs(builds[0] / 'FireSim-generated')
    binding = audit_event_boundary(docs['manifest'], docs['boundary'], docs['mapping'], docs['generated'], text['rtl'], text['bufgce'], text['gate'])
    cuts = [int(v) for v in args.cuts.split(',')]
    monitor = out / 'monitor'
    prepare_monitor(docs['manifest'], docs['boundary'], docs['mapping'], binding, cuts, args.events, monitor)
    inputs = source_inputs(ROOT) | set(paths.values()) | {Path(__file__).resolve()}
    archive = out / 'inputs'; archive.mkdir(); snapshots = {}
    for index, path in enumerate(sorted(inputs)):
        saved = archive / f'{index:04d}-{path.name}'; shutil.copyfile(path, saved)
        snapshots[str(path)] = dict(path=str(saved), sha256=file_sha(saved))
    subprocess.run(['cp', '-a', '--reflink=auto', str(args.seed_build.resolve()), str(out / 'build')], check=True)
    recipe = recipe_settings(RECIPES['Rocket'])
    command = native_build_command(recipe, out / 'build', 'vcs', semantic_root='FireSim.chiptop0',
                                   htif_source=ROOT / 'toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc')
    command['argv'][2] += ' SEMANTIC_MULTICLOCK_INVENTORY=1 SEMANTIC_FAME_STATE_MAP=1 ' + shlex.join([
        'VCS_EXTRA_V=' + str(monitor / 'capture.sv') + ' ' + str(ROOT / 'tools/checkpoint_formats/fame_capture.cc') +
        ' ' + str(ROOT / 'tools/checkpoint_formats/semantic_restore.cc'), 'VCS_FLAGS=-Mupdate -debug_access+all +vpi'])
    commands = [execute(command, out, 'rocket-vcs-build')]
    build = next((out / 'build/f2').iterdir())
    identity = record_build(recipe, build, out / 'rocket-vcs-build.log', out / 'native-build-identity.json', semantic_event_capture=True)
    for name, suffix in [('mapping', '.semantic-fame-map.json'), ('rtl', '.semantic-fame-emitted.sv'),
                         ('manifest', '.semantic-state.json'), ('boundary', '.semantic-boundary.json'), ('clean', '.semantic-clean.sv')]:
        require(file_sha(paths[name]) == file_sha(Path(str(build / 'FireSim-generated') + suffix)), 'capture build differs from audited mapping')
    runtime = out / 'runtime'; runtime.mkdir()
    workload = args.workload.resolve()
    workload_report = json.loads((workload / 'summary.json').read_text())
    elf = Path(workload_report['builds']['rocket-quad']['elf'])
    require(workload_report['status'] == 'passed' and workload_report['harts'] == 4 and
            file_sha(elf) == workload_report['builds']['rocket-quad']['sha256'], 'wrong four-hart self-checking workload')
    argv = [str(build / 'FireSim'), '+permissive', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
            '+memsize=17179869184', '+max-cycles=5000000', '+fesvr-step-size=128', '+blkdev-in-mem0=128',
            '+mm_useHardwareDefaultRuntimeSettings_0', '+tracefile=' + str(runtime / 'TRACEFILE'),
            '+fame_capture=' + str(runtime / 'capture'), '+permissive-off', str(elf)]
    command = dict(cwd='.', argv=['bash', '-lc', ENVIRONMENT + 'cd ' + shlex.quote(str(runtime)) + ' && ' + shlex.join(argv)])
    (runtime / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    commands.append(execute(command, out, 'rocket-capture'))
    (runtime / 'native-vcs.log').symlink_to(out / 'rocket-capture.log')
    (runtime / 'exit.json').write_text(json.dumps(dict(returncode=0, checkpoint_acceptance=False)) + '\n')
    audit_path = out / 'workload-audit.json'
    commands.append(execute(dict(cwd='.', argv=['python', '-m', 'tools.checkpoint_formats.tests.audit_rocket_baseline',
        '--runtime', str(runtime), '--workload', str(workload), '--out', str(audit_path)]), out, 'rocket-workload-audit'))
    current = json.loads(audit_path.read_text()); reference = json.loads(args.reference_audit.read_text())
    for key in LABEL_KEYS:
        require(current[key] == reference[key], 'changed actual four-hart capture workload labels: ' + key)
    comparisons = []
    for hart in range(4):
        actual, original = runtime / f'TRACEFILE-C{hart}', args.reference_runtime.resolve() / f'TRACEFILE-C{hart}'
        require(actual.stat().st_size == original.stat().st_size and file_sha(actual) == file_sha(original), 'changed complete four-hart trace')
        comparisons.append(dict(actual=str(actual), reference=str(original), sha256=file_sha(actual)))
    log = (out / 'rocket-capture.log').read_text()
    require('*** PASSED *** after 3329794 cycles' in log and 'CAPTURE_COMPLETE' in log and
            log.count('FAME_CAPTURE_PRE_EDGE_READBACK words=318637') == len(cuts), 'incomplete actual CPU event capture')
    for cycle in cuts:
        require(f'CAPTURE_WINDOW cycle={cycle} events={args.events}' in log, 'missing complete CPU capture window')
    for path, row in snapshots.items():
        require(file_sha(path) == row['sha256'], 'source changed during complete CPU capture')
    for path, digest in identity['sources_sha256'].items():
        require(file_sha(path) == digest, 'native build input changed during complete CPU capture')
    summary = dict(status='passed', artifact_root=str(out), binding=binding, recipe=recipe, commands=commands,
                   cuts=cuts, events=args.events, native_identity=str(out / 'native-build-identity.json'),
                   workload_sha256=file_sha(elf), comparisons=comparisons, archived_inputs=snapshots,
                   CPU_level1_verified=False, CPU_level2_verified=False)
    summary['artifacts'] = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file() and
                            p.suffix in ('.log', '.json', '.sv', '.state', '.jsonl')}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', summary=str(out / 'summary.json'))))


if __name__ == '__main__':
    main()
