"""Independently audit complete ordinary/restricted syscall-93 CPU executions."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.cpu_recipe import ROOT, RECIPES, recipe_settings
from tools.checkpoint_formats.cpu_native import VCS_HOME, vcs_invocation
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input

MODES = ('ordinary', 'ordinary-buffered', 'restricted', 'restricted-buffered')


def audit(path):
    path = Path(path).resolve(); out = path.parent
    r = json.loads(path.read_text())
    native_root = Path(r.get('native_artifact_root', str(out)))
    require(r['status'] == 'passed' and r['artifact_root'] == str(out) and
            not r['level1_verified'] and not r['level2_verified'], 'wrong CPU control scope')
    bindings = {b['path']: b for b in r['source_inputs']}
    required = [str(Path(__file__)), str(Path(__file__).with_name('verify_rocket_syscall_vcs.py')),
                str(Path(__file__).with_name('verify_rocket_workload.py')),
                str(Path(__file__).with_name('audit_rocket_baseline.py')),
                str(Path(__file__).with_name('exec_with_blocked_htif_signals.py'))]
    require(len(bindings) == len(r['source_inputs']) and all(p in bindings for p in required), 'missing CPU control inputs')
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed CPU control snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    if 'completed_native_summary' in r:
        original = Path(r['completed_native_summary'])
        require(original.parent == native_root and file_sha(original) == r['completed_native_summary_sha256'],
                'changed completed native summary')
        prior = json.loads(original.read_text())
        require(prior['recipe'] == r['recipe'] and prior['workload'] == r['workload'] and
                prior['source_inputs'] == r['native_source_inputs'], 'unbound original native inputs')
        old = {b['path']: b for b in r['native_source_inputs']}
        for b in old.values():
            require(file_sha(b['snapshot']) == b['sha256'], 'changed native execution source snapshot')
            check_native_input(ROOT, b['path'], b['sha256'], old)
        require(set(r['native_artifact_sha256']) == {str(p) for p in native_root.rglob('*') if p.is_file()},
                'native execution artifact membership')
        for p, digest in r['native_artifact_sha256'].items(): require(file_sha(p) == digest, 'changed completed native artifact')
    else:
        require(native_root == out, 'unbound external native root')
    identity = json.loads(Path(r['recipe']).read_text()); binary = Path(identity['native_binary'])
    require(identity['recipe'] == recipe_settings(RECIPES['Rocket']) and identity['vcs_home'] == VCS_HOME and
            identity['htif_lifecycle_provider_linked'] and identity['checkpoint_profile'] is None,
            'wrong CPU control build')
    for p, digest in identity['sources_sha256'].items():
        require(bindings[p]['sha256'] == digest, 'wrong executed native input')
    command, _ = vcs_invocation((Path(r['recipe']).parent/'rocket-vcs-build.log').read_text(), binary)
    require(command == identity['vcs_build_command'], 'unbound native VCS invocation')
    workload = Path(r['workload']); image = json.loads((workload/'summary.json').read_text())
    require(image['status'] == 'passed' and image['exit_protocol'] == 'syscall93' and image['harts'] == 4 and
            image['phases'] == ['early', 'warm', 'memory', 'late'] and image['bytes_per_hart'] == 65536,
            'wrong workload scope')
    commands = json.loads((workload/'commands.json').read_text())
    require(len(commands) == 12 and all(c['returncode'] == c['expected'] for c in commands), 'incomplete workload compilation/Spike scope')
    for hart in (None, 0, 1, 2, 3):
        name = 'rocket-quad' if hart is None else f'corrupt-hart-{hart}'
        build = image['builds'][name]; expected = 0 if hart is None else 1 << hart
        require(file_sha(build['elf']) == build['sha256'] and build['spike_exit'] == expected and
                any(c['argv'] == [image['spike'], '-p4', '--isa=rv64ima_zicsr', build['elf']] and
                    c['returncode'] == expected for c in commands), 'missing actual Spike workload/fault')
    require(file_sha(image['compiled_source']) == image['compiled_source_sha256'], 'changed compiled workload source')
    expected_purposes = {mode+suffix for mode in MODES for suffix in ('-workload', '-audit')}
    # Native execution and later re-auditing may use different PID namespaces
    # or reuse an OS PID. Require distinct processes within each launch phase;
    # every individual result also binds its actual command, log and runtime.
    require(len(r['commands']) == 8 and {c['purpose'] for c in r['commands']} == expected_purposes and
            all(len({c['pid'] for c in r['commands'] if c['purpose'].endswith(suffix)}) == 4
                for suffix in ('-workload', '-audit')), 'incomplete/duplicate CPU processes')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'wrong CPU artifact membership')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed CPU artifact '+p)
    for c in r['commands']:
        text = Path(c['log']).read_text()
        require(c['returncode'] == 0 and text.rstrip().endswith('exit=0') and
                json.loads(text.splitlines()[0]) == {k: c[k] for k in ('cwd', 'argv')} and
                'fresh_process_pid='+str(c['pid']) in text, 'unbound CPU execution')
    receipts = Path(tempfile.mkdtemp(prefix='independent-', dir=out.parent))
    oracle = None; cycles = {}; comparisons = []
    label_keys = ('hart_phases', 'completed_harts', 'failure_stores', 'tohost_stores',
                  'workload_retirements', 'exit_request_stores', 'exit_request_initialization_stores')
    for mode in MODES:
        runtime = native_root/mode
        ran = next(c for c in r['commands'] if c['purpose'] == mode+'-workload')
        require(json.loads((runtime/'command.json').read_text()) == {k: ran[k] for k in ('cwd', 'argv')}, 'changed CPU runtime command')
        shell = ran['argv'][-1]
        require(ran['argv'][:2] == ['bash', '-lc'] and shell.startswith(
            'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && '),
            'VCS environment not sourced last')
        launch = shlex.split(shell.rsplit(' && ', 1)[1]); argv = launch[launch.index('--')+1:]
        require('tools.checkpoint_formats.tests.exec_with_blocked_htif_signals' in launch and argv[0] == str(binary) and
                argv[-2:] == ['+permissive-off', image['builds']['rocket-quad']['elf']] and
                ('+checkpoint-syscall-exit' in argv) == mode.startswith('restricted') and
                ('+tracerv-checkpoint-buffered' in argv) == mode.endswith('buffered') and
                all(v in argv for v in ('-no_save', '+vcs+initreg+0', '+vcs+initmem+0', '+memsize=17179869184',
                    '+max-cycles=5000000', '+fesvr-step-size=128', '+blkdev-in-mem0=128',
                    '+mm_useHardwareDefaultRuntimeSettings_0', '+checkpoint-terminal-input='+str(runtime/'input.bin'))),
                'wrong executed CPU control protocol/settings')
        text = Path(ran['log']).read_text()
        require('TEST_HTIF_SIGNAL_POLICY blocked=SIGINT,SIGTERM,SIGABRT pending=0 before_exec=1' in text,
                'missing pre-thread signal policy')
        labels = re.findall(r'\*\*\* PASSED \*\*\* after (\d+) cycles', text)
        require(len(labels) == 1, 'missing real CPU completion')
        cycles[mode] = int(labels[0])
        receipt = receipts/(mode+'.json')
        subprocess.run([sys.executable, '-m', 'tools.checkpoint_formats.tests.audit_rocket_baseline',
                        '--runtime', str(runtime), '--workload', str(workload), '--out', str(receipt)],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        actual = json.loads(receipt.read_text())
        selected_audit = out/(mode+'-audit.json') if 'completed_native_summary' in r else runtime/'audit.json'
        require(actual == json.loads(selected_audit.read_text()), 'independent CPU decode differs')
        if oracle is None: oracle = actual
        require(all(actual[k] == oracle[k] for k in label_keys), 'CPU target-labelled instructions/stores diverged')
        require((runtime/'input.bin').read_bytes() == b'', 'nonempty sealed terminal input')
        if mode.endswith('buffered'):
            require((runtime/'output.bin').read_bytes() == b'' and
                    (runtime/'heartbeat.csv').read_text().startswith('Target Cycle (fastest), Seconds Since Start\n'),
                    'missing buffered endpoints')
        for hart in range(4):
            trace = runtime/f'TRACEFILE-C{hart}'; reference = native_root/'ordinary'/f'TRACEFILE-C{hart}'
            require(trace.stat().st_size > 0 and file_sha(trace) == file_sha(reference), 'complete hart trace differs')
            comparisons.append(dict(mode=mode, hart=hart, path=str(trace), bytes=trace.stat().st_size, sha256=file_sha(trace)))
    return dict(status='passed', scope='complete uninterrupted four-hart syscall-93 workload controls',
                executions=4, harts_per_execution=4, complete_hart_traces=16, workload_sha256=image['builds']['rocket-quad']['sha256'],
                cycles=cycles, comparisons=comparisons, independent_receipts=str(receipts),
                spike_faults=4, full_backing_memory_bytes_per_execution=17179869184,
                level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', type=Path, required=True)
    a = p.parse_args(); print(json.dumps(audit(a.summary), indent=2))


if __name__ == '__main__':
    main()
