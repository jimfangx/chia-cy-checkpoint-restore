"""Native synthesized physical CE bank, fresh EDA VCS and independent audits.

Component evidence only. The exact Rocket endpoint is exercised with a generated
three-gate workload; it is not a complete Rocket capture or restore adapter.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_state_bank import audit, sha
from tools.checkpoint_formats.tests.audit_physical_clock_wiring import audit as audit_wiring
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SOURCES = (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockStateBank.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutDependencies.scala',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv',
    'tools/checkpoint_formats/tests/physical_clock_state_bank_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
    'tools/checkpoint_formats/tests/audit_physical_clock_state_bank.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_dependencies.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_wiring.py',
    'tools/checkpoint_formats/tests/verify_physical_clock_state_bank.py')
GENERATED = ('reference.fir', 'manifest.json', 'physical-clock-plan.json', 'physical-clock-dependencies.json',
             'physical-clock-state-bank.json', 'physical-clock-state-bank.sv')
NETWORK = ('reference.fir', 'manifest.json', 'physical-clock-plan.json', 'physical-clock-dependencies.json',
           'physical-clock-wiring.fir', 'physical-clock-wiring.json', 'physical-clock-wiring.sv',
           'physical-clock-wiring-emission.json')
TCL = '''set_param general.maxThreads 4
read_verilog -sv sources/CheckpointPhysicalClockCut.sv generated/physical-clock-state-bank.sv network/physical-clock-wiring.sv fixture.sv
synth_design -top PhysicalCEBankSynthesisFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "expected four retained generated native gates"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "wrong native gate semantics"}}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "expected falling-edge common clock mask"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force physical-ce-bank.dcp
puts "PHYSICAL_CE_BANK_SYNTH_PASS gates=4 falling_edge_registers=1"
'''


def fixture(module):
    return '''module PhysicalCEBankSynthesisFixture(
  input wire clock, reset, freeze_request,
  input wire [31:0] descriptor_entry,
  output wire descriptor_valid,
  output wire [7:0] descriptor_bank,
  output wire [15:0] descriptor_slot, descriptor_width,
  output wire [31:0] descriptor_depth,
  input wire request_valid,
  output wire request_ready,
  input wire [7:0] bank,
  input wire [15:0] slot,
  input wire [31:0] address,
  output wire response_valid,
  input wire response_ready,
  output wire [63:0] response_data,
  output wire response_error, stopped, read_enable, failed,
  output wire [63:0] target_cycle, cut_cycle,
  output wire [31:0] state0, state1, state2,
  output wire [2:0] error
);
  wire [2:0] ce, captured_ce, gate_clock;
  wire clock_mask, root_clock;
  PhysicalTransportNetwork network(.clock(clock),.reset(reset),.target_cycle(target_cycle),
    .state0(state0),.state1(state1),.state2(state2),.checkpoint_physical_mask(clock_mask),
    .checkpoint_physical_logical_ce(ce));
  CheckpointPhysicalClockCut #(.GATES(3),.OWNERS(1),.EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock),.reset(reset),.freeze_request(freeze_request),.ce(ce),.target_cycle(target_cycle),
    .owner_present(1'b1),.root_clock(root_clock),.gate_clock(gate_clock),.clock_mask(clock_mask),
    .stopped(stopped),.read_enable(read_enable),.failed(failed),.captured_ce(captured_ce),
    .cut_cycle(cut_cycle),.error(error));
  '''+module+''' endpoint(.*);
endmodule
'''


def check_network(directory):
    audit_dependencies(directory/'reference.fir', directory/'manifest.json', directory/'physical-clock-plan.json',
                       directory/'physical-clock-dependencies.json')
    audit_wiring(*(directory/n for n in ('reference.fir', 'manifest.json', 'physical-clock-plan.json',
        'physical-clock-wiring.fir', 'physical-clock-wiring.json', 'physical-clock-wiring.sv',
        'physical-clock-wiring-emission.json')))
    manifest = json.loads((directory/'physical-clock-plan.json').read_text())
    require(manifest['root_module'] == 'PhysicalTransportNetwork' and len(manifest['physical_gates']) == 3,
            'expected compiler-generated three-gate active fixture')


def negative_layouts(directory, out):
    original = json.loads((directory/'physical-clock-state-bank.json').read_text())
    mutations = {}
    for key in ('complete_fpga_capture', 'deployable_capture_image', 'production_freeze_owners_bound', 'metasim_restore_supported'):
        mutations[key] = lambda d, key=key: d.update({key: True})
    mutations.update(
        missing_owner=lambda d: d['state'].pop(),
        duplicate_slot=lambda d: d['state'][1].update(slot=0),
        swapped_bits=lambda d: d['state'][0].update(ce_bit=1),
        metasim_O_as_physical_id=lambda d: d['state'][0].update(state_id=d['state'][0]['metasim_output_state_id']),
        wrong_bank=lambda d: d['state'][0].update(bank=0),
        wrong_width=lambda d: d['state'][0].update(width=3),
        wrong_depth=lambda d: d['state'][0].update(depth=2),
        missing_reset_contract=lambda d: d.pop('reset_contract'),
        stale_endpoint=lambda d: d.update(endpoint_sha256='0'*64),
        fake_restore_adapter=lambda d: d['state'][0].update(restore_adapter='metasim-bufgce-v1'))
    rejections = []
    for name, mutate in mutations.items():
        work = out/name; shutil.copytree(directory, work)
        doc = json.loads(json.dumps(original)); mutate(doc)
        (work/'physical-clock-state-bank.json').write_text(json.dumps(doc))
        try:
            audit(work)
        except (ValueError, RuntimeError) as e:
            rejections.append(dict(name=name, error=str(e)))
        else:
            raise RuntimeError('accepted corrupt physical bank layout '+name)
    return rejections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    parser.add_argument('--generated', type=Path)
    parser.add_argument('--network', type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--eda', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = args.out.resolve(); require(base.is_relative_to(RUNS), 'evidence below runs required')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=base))
    commands = []
    sources = {n: sha(ROOT/n) for n in SOURCES}

    def run(argv, name, cwd=out, expected=0):
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()

    def validate(directory, backend):
        require(directory is not None and directory.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc = json.loads((directory/'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and doc['sources'] == sources and
                doc['physical_fpga_capture'] is False and doc['full_rocket_image_build'] is False and
                doc['metasim_restore_supported'] is False, 'invalid or stale component receipt')
        for group in ('inputs', 'artifacts'):
            for path, digest in doc[group].items():
                require(sha(directory/path) == digest, 'changed '+group+' '+path)
        for path, digest in sources.items():
            require(sha(directory/'sources'/Path(path).name) == digest, 'changed source snapshot '+path)
        require((directory/'fixture.sv').read_text() == fixture(doc['endpoint_module']) and
                (directory/'synth.tcl').read_text() == TCL, 'changed native composition')
        audit(directory/'generated'); check_network(directory/'network')
        return doc

    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='generated physical CE endpoint with native clocks and active component workload only',
        physical_fpga_capture=False, full_rocket_image_build=False, metasim_restore_supported=False, sources=sources)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost Vivado required')
        for src, name, names in ((args.generated, 'generated', GENERATED), (args.network, 'network', NETWORK)):
            require(src is not None and src.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
            (out/name).mkdir()
            for n in names:
                shutil.copyfile(src/n, out/name/n)
        layout = audit(out/'generated'); check_network(out/'network')
        require(layout['physical_gates'] == 3, 'this execution fixture requires exactly three CE bits')
        doc = json.loads((out/'generated/physical-clock-state-bank.json').read_text())
        summary['endpoint_module'] = doc['endpoint_module']
        (out/'sources').mkdir()
        for n in SOURCES:
            shutil.copyfile(ROOT/n, out/'sources'/Path(n).name)
        (out/'fixture.sv').write_text(fixture(doc['endpoint_module'])); (out/'synth.tcl').write_text(TCL)
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models'] = {}
        for n, src in (('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')):
            shutil.copyfile(src, out/n)
            summary['vendor_models'][n] = dict(original_path=str(src), sha256=sha(src))
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for d in ('sources','generated','network') for p in (out/d).iterdir()}
        summary['inputs'].update({n: sha(out/n) for n in ('fixture.sv','synth.tcl','BUFGCE.v','glbl.v')})
        text = run(['vivado','-mode','batch','-source','synth.tcl','-log','vivado.log','-journal','vivado.jou'], 'synth')
        require('PHYSICAL_CE_BANK_SYNTH_PASS gates=4 falling_edge_registers=1' in text and
                not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native bank/clock synthesis failed')
        summary['layout_audit'] = layout
        summary['layout_rejections'] = negative_layouts(out/'generated', out/'negative-layouts')
        summary['artifacts'] = {n: sha(out/n) for n in ('physical-ce-bank.dcp','utilization.rpt','timing.rpt','synth.log','vivado.log','vivado.jou','commands.json')}
    elif args.mode == 'vcs':
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA VCS SP2 required')
        native = validate(args.native, 'f2'); summary['endpoint_module'] = native['endpoint_module']
        for n, digest in native['inputs'].items():
            p = out/n; p.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.native/n, p)
            require(sha(p) == digest, 'native input copy mismatch')
        healthy = out/'healthy'; healthy.mkdir()
        def compile_bank(work, bank_source, name):
            run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
                 '+define+CE_BANK_MODULE='+native['endpoint_module'], '-top','physical_clock_state_bank_tb','-top','glbl',
                 '-Mdir='+str(work/'csrc'),'-o',work/'simv',out/'BUFGCE.v',out/'glbl.v',
                 bank_source,out/'network/physical-clock-wiring.sv',
                 *(out/'sources'/n for n in ('CheckpointPhysicalClockCut.sv','physical_clock_state_bank_tb.sv',
                                           'checkpoint_generated_network_exit.cc'))], name, work)
        compile_bank(healthy, out/'generated/physical-clock-state-bank.sv', 'compile')
        text = run([healthy/'simv','-no_save'], 'healthy', healthy)
        match = re.search(r'PHYSICAL_CE_BANK_PASS checks=(\d+) cuts=5 reads=(\d+) stalls=140 cycles=320', text)
        require(match is not None, 'incomplete physical bank execution scope')
        require('PHYSICAL_CE_BANK_COVERAGE ones=7 zeros=7' in text, 'missing per-bit zero/one coverage')
        summary.update(checks=int(match[1]), cuts=5, reads=int(match[2]), stalls=140, cycles=320)
        corrupt = out/'corrupt'; corrupt.mkdir()
        text = run([healthy/'simv','-no_save','+corrupt'], 'corrupt', corrupt, expected=1)
        require('reason=deliberately corrupt CE oracle acknowledged_edges=0' in text and
                'PHYSICAL_CE_BANK_PASS' not in text, 'corrupt readback oracle did not stop')
        mutant = out/'mutated-endpoint'; mutant.mkdir()
        source = (out/'generated/physical-clock-state-bank.sv').read_text()
        require(source.count("{63'd0, captured_ce[slot]}") == 1, 'ambiguous endpoint fault site')
        changed = mutant/'physical-clock-state-bank.sv'
        changed.write_text(source.replace("{63'd0, captured_ce[slot]}", "{63'd0, !captured_ce[slot]}"))
        compile_bank(mutant, changed, 'mutated-compile')
        text = run([mutant/'simv','-no_save'], 'mutated-endpoint', mutant, expected=1)
        require('reason=physical CE word acknowledged_edges=0' in text and
                'PHYSICAL_CE_BANK_PASS' not in text, 'wrong synthesized CE bit escaped the independent oracle')
        summary['negative_tests'] = ['corrupt readback oracle', 'inverted synthesized CE bit']
        summary['inputs'] = native['inputs']; summary['native_receipt'] = str(args.native/'summary.json')
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log','.vcd')}
    else:
        native, eda = validate(args.native, 'f2'), validate(args.eda, 'eda')
        require(native['inputs'] == eda['inputs'] and eda['cuts'] == 5 and eda['stalls'] == 140 and eda['cycles'] == 320,
                'different inputs or incomplete EDA execution')
        require(len(list(args.eda.rglob('*.vcd'))) == 3 and
                eda['negative_tests'] == ['corrupt readback oracle', 'inverted synthesized CE bit'],
                'missing healthy/first-divergence scope or full debug waves')
        summary.update(endpoint_module=native['endpoint_module'], native_receipt=str(args.native/'summary.json'),
            eda_receipt=str(args.eda/'summary.json'), matched_inputs=len(native['inputs']), inputs={}, artifacts={})
    require(sources == {n: sha(ROOT/n) for n in SOURCES}, 'source changed during execution')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
