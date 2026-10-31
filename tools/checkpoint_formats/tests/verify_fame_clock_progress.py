"""Native synthesis and EDA VCS for compiler-created FAME progress observations.

Component evidence only: no production cut, image, FPGA capture or CPU restore.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.regression_runner import local

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
SOURCES = [
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/FAMEClockProgress.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/FAMEClockProgressBindings.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockGateContract.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/passes/fame/FAMETransform.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/passes/xilinx/ClockGateRetirement.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCli.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/FAMEClockProgressSpec.scala',
    'tools/checkpoint_formats/tests/fame_clock_progress_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/tests/verify_fame_clock_progress.py',
    'tools/checkpoint_formats/tests/audit_fame_clock_progress.py',
]
GENERATED = ('observed.fir', 'observed.sv', 'probed.sv', 'reference.fir', 'reference.sv', 'state.json',
             'progress-binding.json', 'progress-annotations.json', 'emission-reference.fir')


def audit_binding(generated, binding=None):
    """Independent fixture oracle: bind compiler roles to the raw-wave names.

    These fixed names describe this two-clock test, never production discovery.
    The Scala tests separately exercise native inlining and emitter renaming.
    """
    binding = json.loads((generated / 'progress-binding.json').read_text()) if binding is None else binding
    require(binding['binding_version'] == 1 and binding['scope'] == 'fame-clock-progress-role-map-only'
            and binding['global_target_cut_proven'] is False and binding['capture_supported'] is False,
            'invalid role binding scope')
    for key, name in [('emitted_verilog_sha256', 'observed.sv'),
                      ('emission_reference_sha256', 'emission-reference.fir'),
                      ('generated_manifest_sha256', 'state.json')]:
        require(binding[key] == file_sha(generated / name), 'role binding input hash differs: ' + name)
    annotations = json.loads((generated / 'progress-annotations.json').read_text())
    models = [a for a in annotations if a['class'].endswith('.FAMEClockProgressModelAnnotation')]
    require(len(models) == 1 and models[0]['model'] == '~Top|Model' and models[0]['domains'] == ['clockA', 'clockB'],
            'construction-site identity differs')
    signals = [a for a in annotations if a['class'].endswith('.FAMEClockProgressSignalAnnotation')]
    expected = {('', role): ('hostClock' if role == 'host_clock' else 'hostReset' if role == 'host_reset'
                            else 'targetCycleFinishing' if role == 'finishing' else 'checkpoint_fame_' + role)
                for role in ('host_clock', 'host_reset', 'finishing', 'completed_steps', 'overflow')}
    for clock in ('clockA', 'clockB'):
        expected.update({(clock, role): 'checkpoint_fame_' + clock + '_' + role
                         for role in ('consume', 'launch', 'pending', 'consumed', 'applied')})
        expected.update({(clock, 'pending_flag'): clock + '_enabled',
                         (clock, 'gate_ce'): clock + '_buffer.CE', (clock, 'gate_output'): clock + '_buffer.O'})
    rows = binding['signals']
    require(len(rows) == len(signals) == len(expected) == 21, 'incomplete or duplicated roles')
    by_key = {(r['domain_identity'], r['role']): r for r in rows}
    require(set(by_key) == set(expected), 'unknown or missing role')
    storage = {e['hierarchy']: e for e in json.loads((generated / 'state.json').read_text())['state']}
    stored_bits = 0
    for key, ref in expected.items():
        row = by_key[key]
        require(row['model_identity'] == '~Top|Model' and row['rtl_path'] == 'Top.model_.' + ref,
                'role path differs from independently observed waveform location')
        matches = [a for a in signals if (a['domain'], a['role']) == key]
        require(len(matches) == 1 and matches[0]['model'] == row['model_identity']
                and matches[0]['target'] == row['target'], 'role target differs from native rename result')
        stored = key[1] in ('completed_steps', 'overflow', 'consumed', 'applied', 'pending_flag')
        require(row['storage'] is stored, 'role storage kind differs')
        if stored:
            entry = storage[row['rtl_path']]
            require(row['generated_state_id'] == entry['state_id'] and entry['kind'] == 'register'
                    and entry['depth'] == 1 and entry['width'] == (64 if key[1] in ('completed_steps', 'consumed', 'applied') else 1),
                    'role not bound to complete inventoried storage')
            stored_bits += entry['width']
    require(stored_bits == 323, 'observer and original pending flags incomplete')
    return dict(roles=len(rows), observer_bits=321, original_pending_bits=2, global_target_cut_proven=False)
TCL = '''set_param general.maxThreads 4
read_verilog -sv probed.sv
synth_design -top Top -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports hostClock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 2} {error "two original FAME gates required"}
set observers [get_cells -hier -filter {NAME =~ *checkpoint_fame* && IS_SEQUENTIAL == 1}]
if {[llength $observers] != 321} {error "all five 64-bit counters and overflow must survive"}
report_utilization -file synth-utilization.rpt
write_checkpoint -force synthesized.dcp
set original [lsort [get_property NAME [get_cells -hier -filter {IS_SEQUENTIAL == 1}]]]
set_property DONT_TOUCH true [get_cells $original]
opt_design
place_design
phys_opt_design
route_design
if {$original ne [lsort [get_property NAME [get_cells -hier -filter {IS_SEQUENTIAL == 1}]]]} {error "sequential identity changed"}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
report_route_status -file route-status.rpt
report_drc -file drc.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
puts "FAME_PROGRESS_TIMING setup_ns=$setup hold_ns=$hold sequential=[llength $original]"
write_checkpoint -force implemented.dcp
if {$setup < 0 || $hold < 0} {error "component failed unchanged 140 MHz timing"}
puts "FAME_PROGRESS_NATIVE_PASS observer_bits=321 gates=2"
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(RUNS), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    generated = local(ROOT, args.generated).resolve()
    require(generated.is_relative_to(RUNS), 'compiler fixture outside runs')
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT),
               physical_fpga_capture=False, deployable_capture_image=False, global_target_cut_proven=False,
               scope='compiler FAME clock progress component', commands=[],
               sources={n: file_sha(ROOT / n) for n in SOURCES},
               generated_path=str(generated), generated={n: file_sha(generated / n) for n in GENERATED})

    def run(argv, name, work=out, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log: ' + str(log))
        return log.read_text()

    try:
        doc['role_binding'] = audit_binding(generated)
        # Every role must fail if coherently retargeted to another waveform
        # location, even when the native execution files remain unchanged.
        import copy
        binding = json.loads((generated / 'progress-binding.json').read_text())
        rejected = 0
        for index in range(len(binding['signals'])):
            bad = copy.deepcopy(binding)
            bad['signals'][index]['rtl_path'] = binding['signals'][(index + 1) % len(binding['signals'])]['rtl_path']
            try:
                audit_binding(generated, bad)
            except ValueError:
                rejected += 1
            else:
                raise ValueError('retargeted compiler role accepted')
        doc['rejected_role_path_mutations'] = rejected
        for n in GENERATED:
            shutil.copyfile(generated / n, out / n)
        for n in SOURCES:
            shutil.copyfile(ROOT / n, out / Path(n).name)
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'Vivado must run on current manager')
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
            doc['vendor_models'] = {}
            for name, source in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
                shutil.copyfile(source, out / name)
                doc['vendor_models'][name] = dict(original_path=str(source), sha256=file_sha(source))
            (out / 'synth.tcl').write_text(TCL)
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'native')
            match = re.search(r'FAME_PROGRESS_TIMING setup_ns=([-0-9.]+) hold_ns=([-0-9.]+) sequential=(\d+)', text)
            require(match and 'Vivado v2025.2' in text and 'FAME_PROGRESS_NATIVE_PASS observer_bits=321 gates=2' in text
                    and not re.search('ERROR:|CRITICAL WARNING:', text), 'native closure incomplete')
            doc['timing'] = dict(setup_ns=float(match[1]), hold_ns=float(match[2]), sequential=int(match[3]),
                                 requested_mhz=140, shell_io_and_parent_timing_proven=False)
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'VCS must run on EDA')
            native = local(ROOT, args.native).resolve()
            receipt = native / 'summary.json'
            bound = json.loads(receipt.read_text())
            require(bound['status'] == 'pass' and bound['backend'] == 'f2' and
                    bound['sources'] == doc['sources'] and bound['generated'] == doc['generated'], 'native source/generated binding differs')
            for n, digest in bound['artifacts'].items():
                path = (native / n).resolve()
                require(path.is_relative_to(native) and file_sha(path) == digest, 'native artifact changed: ' + n)
            require((native / 'synth.tcl').read_text() == TCL, 'native contract changed')
            doc['native_receipt'] = dict(path=str(receipt), sha256=file_sha(receipt))
            for n in ('BUFGCE.v', 'glbl.v'):
                shutil.copyfile(native / n, out / n)
            reference = (out / 'reference.sv').read_text()
            for n in ('Top', 'Model'):
                reference = re.sub(r'\b' + n + r'\b', 'Reference' + n, reference)
            (out / 'reference-renamed.sv').write_text(reference)
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-debug_access+all',
                 '-debug_region+cell+encrypt', '-Mupdate', '-top', 'fame_clock_progress_tb', '-top', 'glbl',
                 '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv',
                 *[out / n for n in ('BUFGCE.v', 'glbl.v', 'observed.sv', 'reference-renamed.sv', 'fame_clock_progress_tb.sv')],
                 out / 'checkpoint_widget_exit.cc', '-CFLAGS', '-std=c++17'], 'compile')
            doc['cases'] = {}
            for case, extra in [('healthy', []), ('corrupt', ['+corrupt']),
                                *[('overflow-' + str(i), ['+overflow=' + str(i)]) for i in range(5)]]:
                work = out / case; work.mkdir()
                text = run([out / 'simv', '-no_save', *extra], case, work, 1 if case == 'corrupt' else 0)
                if case == 'corrupt':
                    require('FAME_PROGRESS_DIVERGENCE host_step=17 acknowledged=16 signal=clockA_applied' in text,
                            'missing first-divergence observation')
                else:
                    require(re.search(r'FAME_PROGRESS_PASS checks=\d+ cycles=512 ', text), 'component execution incomplete')
                require((work / 'fame-progress.vcd').stat().st_size > 1000, 'full debug waveform missing')
                doc['cases'][case] = dict(log=str(out / (case + '.log')), waveform=str(work / 'fame-progress.vcd'))
        require(doc['sources'] == {n: file_sha(ROOT / n) for n in SOURCES}, 'sources changed during execution')
        require(doc['generated'] == {n: file_sha(generated / n) for n in GENERATED}, 'compiler outputs changed')
        doc['status'] = 'pass'
    except Exception as error:
        doc['error'] = str(error)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): file_sha(p) for p in out.rglob('*')
                            if p.is_file() and p.suffix in {'.log', '.rpt', '.sv', '.v', '.cc', '.scala', '.fir', '.json', '.tcl', '.dcp', '.vcd'}}
        receipt = out / 'summary.json'
        receipt.write_text(json.dumps(doc, indent=2) + '\n')
        print(receipt, flush=True)


if __name__ == '__main__':
    main()
