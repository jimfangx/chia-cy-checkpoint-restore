"""Reserved driver creator, native sanitizers and actual pre-edge VCS harness.

Exercises both legacy paths and both reserved paths without claiming CPU restore.
"""
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
from tools.checkpoint_formats.native_regressions import source_inputs
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    a = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    require(a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    cc = ROOT/'sims/firesim/sim/midas/src/main/cc'; tests = Path(__file__).resolve().parent
    generated = a.build.resolve()/'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'
    inputs = source_inputs(ROOT) | {p for p in generated.iterdir() if p.is_file() and
                                  p.suffix in ('.sv', '.vh', '.json', '.fir')}
    (out/'sources').mkdir(); bindings = []
    for p in sorted(inputs):
        digest = file_sha(p); saved = out/'sources'/digest
        if not saved.exists(): shutil.copyfile(p, saved)
        bindings.append(dict(path=str(p), sha256=digest, snapshot=str(saved)))
    (out/'source-inputs.json').write_text(json.dumps(bindings, indent=2)+'\n')
    def execute(argv, name):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        log = out/(name+'.log'); run(command, log)
        return dict(argv=command, cwd='.', log=str(log))
    source = tests/'driver_creator_reservation.cc'
    allocations = tests/'tsi_terminal_allocations.cc'
    commands = [execute([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-g',
                        '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I'+str(cc), source, allocations, '-pthread', '-o', out/'native'], 'native-build')]
    commands += [execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog',
                          '-timescale=1ns/1ps', '-top', 'driver_creator_reservation_tb',
                          '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
                          '-Mdir='+str(out/'csrc'), '-CFLAGS', '-std=c++17 -DDRIVER_CREATOR_DPI -I'+str(cc),
                          '-LDFLAGS', '-pthread', '-o', out/'simv',
                          tests/'driver_creator_reservation_tb.sv', source, allocations], 'vcs-build')]
    for name, argv in [('native', [out/'native']), ('vcs', [out/'simv', '-no_save'])]:
        receipt = execute(argv, name); commands.append(receipt)
        text = Path(receipt['log']).read_text()
        require('DRIVER_CREATOR_PASS tasks=512 exceptions=512 launches=17 cancellations=16 rejections=1296' in text,
                'creator lifecycle cases missing')
        require('DRIVER_RESIDENT_PASS destroyed=32 launches=16 cancellations=16 exceptions=32 rejections=176 capture_order=1' in text,
                'creator retained lifetime cases missing')
        require('DRIVER_PREPARED_LAUNCH_PASS destroyed=32 launches=16 cancellations=16 allocation_failures=32 rejections=208 allocation_free_commit=1 capture_order=1' in text,
                'creator launch preparation missing')
        require(not any(s in text for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')),
                'creator sanitizer failure')
        if name == 'vcs': require('DRIVER_CREATOR_ZERO_EDGES time=0 edges=0' in text, 'VCS preparation edge')
    def harness(options):
        name = 'harness'+('-aggregate' if options[0] else '')+('-reserved' if options[1] else '-legacy')
        dest = out/name
        receipt = execute(['python', '-m', 'tools.checkpoint_formats.tests.verify_harness_dispatcher_vcs',
                           '--build', a.build.resolve(), '--out', dest,
                           *(['--aggregate'] if options[0] else []),
                           *(['--creator-reservation'] if options[1] else [])], name)
        report = json.loads((dest/'summary.json').read_text())
        require(report['fresh_continuations'] == 5 and report['malformed_native_processes'] == 35 and
                report['lifecycle_negative_processes'] == 20, 'incomplete harness cases')
        if options[1]:
            require(report['reserved_creator_continuations'] == 5 and
                    report['creator_preparation_guards'] == 65, 'reserved harness missing')
            for cut in (13,14,16,31,32):
                trace=(dest/f'cut-{cut}/restore/run.log').read_text()
                require('HARNESS_CREATOR_RESOURCE_LIVE same_thread=1 finalized=1' in trace and
                        'HARNESS_CREATOR_RESOURCE_DESTROYED same_thread=1 finalized=1' in trace,
                        'missing actual harness resident lifetime')
        return dict(receipt, summary=str(dest/'summary.json'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        commands += list(pool.map(harness, [(False, False), (True, False), (False, True), (True, True)]))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'source changed during creator check '+b['path'])
    report = dict(status='passed', scope='pre-edge driver creator component; CPU restore remains unsupported',
                  commands=commands, source_inputs=bindings, harness_continuations=20,
                  reserved_creator_continuations=10, malformed_native_processes=140,
                  lifecycle_negative_processes=80, aggregate_prevalidation_rejections=140,
                  creator_preparation_guards=130, level1_verified=False, level2_verified=False,
                  creator_resource_retained=True,
                  creator_launch_prepared=True,
                  artifact_sha256={str(p):file_sha(p) for p in out.rglob('*') if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    from tools.checkpoint_formats.tests.audit_driver_creator import audit
    try: audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(status='passed', summary=str(path)), indent=2))


if __name__ == '__main__': main()
