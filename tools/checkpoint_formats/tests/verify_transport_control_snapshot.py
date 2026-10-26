"""Atomic transport shadow component: localhost synthesis and EDA-only VCS.

Never admits a production image or claims FPGA-origin checkpoint acceptance.
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
from tools.checkpoint_formats.tests import verify_transport_control_state as control

ROOT, RUNS, RTL, EXIT = control.ROOT, control.RUNS, control.RTL, control.EXIT
SNAPSHOT = 'sims/firesim/sim/midas/src/main/verilog/CheckpointTransportControlSnapshot.sv'
TB = 'tools/checkpoint_formats/tests/transport_control_snapshot_tb.sv'
SELF = 'tools/checkpoint_formats/tests/verify_transport_control_snapshot.py'
SOURCES = (*control.SOURCES, SNAPSHOT, TB, SELF)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture(generated):
    text = control.fixture(generated).replace('ControlStateSynthesisFixture', 'ControlSnapshotSynthesisFixture')
    text = text.replace('    input wire [31:0] word_index,', '''    input wire snapshot_cut_valid, snapshot_owner_error, snapshot_request,
    input wire snapshot_release, snapshot_abort,
    input wire [31:0] snapshot_word_index,
    output wire snapshot_ready, snapshot_valid, snapshot_word_valid,
    output wire [63:0] snapshot_word_data, snapshot_cycle,
    output wire [2:0] snapshot_error,
    input wire [31:0] word_index,''')
    return text.replace('endmodule', '''  CheckpointTransportControlSnapshot #(.GATES(3)) snapshot(
    .clock(clock), .reset(reset), .live_state(control_state), .target_cycle(target_cycle),
    .cut_valid(snapshot_cut_valid), .owner_error(snapshot_owner_error),
    .request_valid(snapshot_request), .request_ready(snapshot_ready),
    .release_snapshot(snapshot_release), .abort_snapshot(snapshot_abort),
    .snapshot_valid(snapshot_valid), .snapshot_cycle(snapshot_cycle), .error(snapshot_error),
    .word_index(snapshot_word_index), .word_valid(snapshot_word_valid), .word_data(snapshot_word_data));
endmodule''')


def tcl():
    text = control.tcl().replace(' bank.sv fixture.sv', ' snapshot.sv bank.sv fixture.sv')
    text = text.replace('-top ControlStateSynthesisFixture', '-top ControlSnapshotSynthesisFixture')
    text = text.replace('set regs [get_cells -hier -filter {REF_NAME =~ FD*}]',
                        'set regs [get_cells -hier -filter {REF_NAME =~ FD* && NAME !~ snapshot/*}]')
    audit = '''set shadow [get_cells -hier -filter {REF_NAME =~ FD* && NAME =~ snapshot/*}]
set expected_shadow [expr {484 + 64 + 1 + 3}]
if {[llength $shadow] != $expected_shadow} {error "lost or unexpected shadow storage"}
set sf [open snapshot-registers.tsv w]
set classified {}
foreach {field count} {saved_state 484 snapshot_cycle 64 occupied 1 error 3} {
  set selected [get_cells -hier -filter "NAME =~ snapshot/${field}_reg* && REF_NAME =~ FD*"]
  if {[llength $selected] != $count} {error "incorrect shadow field $field"}
  foreach cell $selected {
    set pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[llength $pin] != 1 || [get_property IS_INVERTED $pin] != 0 ||
        [lsearch -exact [get_nets -segments -of_objects $pin] $raw] < 0} {error "shadow lost raw posedge $cell"}
    if {[get_property FSM_ENCODED_STATES $cell] ne ""} {error "unmapped shadow FSM encoding $cell"}
    lappend classified $cell
    puts $sf "$field\t$cell\t[get_property REF_NAME $cell]\t[get_property FILE_NAME $cell]\t[get_property LINE_NUMBER $cell]"
  }
}
close $sf
if {[lsort $shadow] ne [lsort $classified]} {error "unclassified shadow state"}
set all [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[lsort $all] ne [lsort [concat $observed $classified]]} {error "unclassified complete fixture state"}
puts "SNAPSHOT_SYNTH_PASS fields=4 registers=[llength $shadow] total_registers=[llength $all] raw_positive_edge=1"
'''
    return text.replace('report_utilization -file', audit+'report_utilization -file')


def monitor(generated):
    # Independent pre-edge hierarchy oracle. Neither the shadow storage nor the
    # exported vector is used to construct the expected captured register image.
    rows = control.reconstruct({Path(n).name: (ROOT/n).read_text() for n in RTL}, 3)
    packed = ', '.join('dut.'+r['relative_path'] for r in rows[::-1])
    # DPI failure intentionally bypasses VCS cleanup. Preserve the actual
    # negative waveform through its divergent word before the nonzero exit.
    text = control.monitor(generated).replace('checkpoint_network_fail(); $fatal',
                                             '$dumpflush; #0.001; checkpoint_network_fail(); $fatal')
    require(text.count('import "DPI-C" function void checkpoint_network_fail();') == 1,
            'failure-call instrumentation changed the DPI declaration')
    marker = '  integer checks=0'
    injection = '''  wire shadow_ready, shadow_valid, shadow_word_valid;
  wire [63:0] shadow_word_data, shadow_cycle;
  wire [2:0] shadow_error;
  reg [31:0] shadow_index=0;
  reg shadow_taken=0;
  wire shadow_cut=physical_read_enable && (&owner_frozen) && !(|owner_error);
  wire shadow_request=shadow_cut && !shadow_taken;
  // Discard after checking words through the stopped transport's activity.
  // Use the epoch marker rather than snapshot_valid: release immediately
  // invalidates the public valid signal and must not feed back through it.
  wire shadow_release=shadow_taken && !freeze && !physical_stopped;
  reg [483:0] shadow_expected;
  reg [63:0] shadow_expected_cycle;
  integer shadow_captures=0, shadow_checks=0, shadow_live_changes=0;
  CheckpointTransportControlSnapshot #(.GATES(3)) shadow(
    .clock(clock),.reset(reset),.live_state(control_state),.target_cycle(target_cycle),
    .cut_valid(shadow_cut),.owner_error(|owner_error),.request_valid(shadow_request),
    .request_ready(shadow_ready),.release_snapshot(shadow_release),.abort_snapshot(1'b0),
    .snapshot_valid(shadow_valid),.snapshot_cycle(shadow_cycle),.error(shadow_error),
    .word_index(shadow_index),.word_valid(shadow_word_valid),.word_data(shadow_word_data));
  always @(posedge clock) begin
    if(reset) shadow_taken<=0;
    else begin
      if(!physical_stopped && !freeze) shadow_taken<=0;
      if(shadow_request && shadow_ready) begin
        shadow_expected={PACKED};
        shadow_expected_cycle=target_cycle;
        shadow_captures++;
        shadow_taken<=1;
      end
    end
    #2;
    if(shadow_error!==0) begin
      $display("SHADOW_DIVERGENCE cycle=%0d signal=error",target_cycle);
      $dumpflush; #0.001;
      checkpoint_network_fail(); $fatal(1,"unexpected shadow protocol fault");
    end
    if(shadow_valid) begin
      if(shadow_cycle!==shadow_expected_cycle) begin
        $display("SHADOW_DIVERGENCE cycle=%0d signal=cut_cycle",target_cycle);
        $dumpflush; #0.001;
        checkpoint_network_fail(); $fatal(1,"shadow label");
      end
      if(control_state!==shadow_expected) shadow_live_changes++;
      for(integer sw=0;sw<10;sw++) begin
        shadow_index=sw; #0.001;
        if(shadow_word_valid!==(sw<8) || shadow_word_data!==
            (sw<8 ? (shadow_expected >> (64*sw)) & 64'hffffffffffffffff : 64'b0)) begin
          $display("SHADOW_DIVERGENCE cycle=%0d signal=word word=%0d",target_cycle,sw);
          $dumpflush; #0.001;
          checkpoint_network_fail(); $fatal(1,"shadow word");
        end
        shadow_checks++;
      end
    end
  end
  final $display("SHADOW_AUDIT_PASS captures=%0d word_checks=%0d live_changes=%0d",shadow_captures,shadow_checks,shadow_live_changes);
'''.replace('PACKED', packed)
    require(text.count(marker) == 1, 'integration monitor injection boundary changed')
    return text.replace(marker, injection+marker)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['vivado', 'vcs', 'audit'], required=True)
    for name in ('generated', 'native', 'eda', 'out'):
        p.add_argument('--'+name, type=Path, required=name in ('generated', 'out'))
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    a.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=a.mode+'-', dir=a.out.resolve()))
    sources = {n: sha(ROOT/n) for n in SOURCES}
    control.audit(a.generated)
    commands = []

    def run(argv, name, expected=0, cwd=out):
        log = out/(name+'.log')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log))
        commands.append(row)
        with log.open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'inspect underlying compiler/runtime log '+str(log))
        return log.read_text()

    def validate(directory, backend):
        doc = json.loads((directory/'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and doc['sources'] == sources and
                doc['physical_fpga_capture'] is False and doc['production_transport_owner'] is False and
                doc['restore_adapter'] is False, 'stale/false shadow receipt')
        for group in ('inputs', 'artifacts'):
            for name, digest in doc[group].items():
                require(sha(directory/name) == digest, 'changed evidence '+name)
        return doc

    summary = dict(status='pass', backend='eda' if a.mode == 'vcs' else 'f2', sources=sources,
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='atomic transport register shadow component only',
                   physical_fpga_capture=False, production_transport_owner=False, restore_adapter=False)
    if a.mode == 'vivado':
        require(str(ROOT) == '/home/ubuntu/chia-cy-checkpoint-restore' and shutil.which('vivado'), 'localhost Vivado required')
        for n in (*RTL, SNAPSHOT, EXIT, TB):
            dst = out/'sources'/Path(n).name
            dst.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT/n, dst)
        shutil.copyfile(ROOT/SNAPSHOT, out/'snapshot.sv')
        shutil.copyfile(a.generated/'control-state-bank-3.sv', out/'bank.sv')
        (out/'fixture.sv').write_text(fixture(a.generated))
        (out/'synth.tcl').write_text(tcl())
        (out/'monitor.sv').write_text(monitor(a.generated))
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for name, src in [('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')]:
            shutil.copyfile(src, out/name)
        summary['inputs'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*') if f.is_file()}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        m = re.search(r'SNAPSHOT_SYNTH_PASS fields=4 registers=552 total_registers=(\d+) raw_positive_edge=1', text)
        require(m and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'incomplete native atomic shadow synthesis')
        summary.update(shadow_registers=552, total_registers=int(m[1]))
        summary['artifacts'] = {n: sha(out/n) for n in ('synth.log', 'state-registers.tsv',
            'state-native-encodings.tsv', 'snapshot-registers.tsv', 'control-state.dcp',
            'control-state-netlist.v', 'utilization.rpt', 'timing.rpt', 'commands.json')}
    elif a.mode == 'vcs':
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA SP2 VCS required')
        native = validate(a.native, 'f2')
        for name in native['inputs']:
            dst = out/name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(a.native/name, dst)
        common = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all']
        results = []
        for gates in (1, 3, 65):
            work = out/('standalone-'+str(gates))
            work.mkdir()
            run([*common, '+define+SNAPSHOT_GATES='+str(gates), '-top', 'transport_control_snapshot_tb',
                 '-Mdir='+str(work/'csrc'), '-o', work/'simv', out/'snapshot.sv',
                 out/'sources'/Path(TB).name, out/'sources'/Path(EXIT).name], 'compile-'+str(gates))
            text = run([work/'simv', '-no_save'], 'standalone-'+str(gates), cwd=work)
            m = re.search(r'SNAPSHOT_PASS gates=(\d+) bits=(\d+) captures=(\d+) checks=(\d+) word_checks=(\d+)', text)
            require(m and int(m[1]) == gates and int(m[2]) == 481+gates and
                    int(m[3]) == 481+gates+34 and int(m[5]) == int(m[3])*6*((481+gates+63)//64),
                    'incomplete exhaustive shadow coverage')
            results.append(dict(gates=gates, captures=int(m[3]), checks=int(m[4]), word_checks=int(m[5])))
        argv = [*common, '-top', 'physical_capture_transport_tb', '-top', 'glbl',
                '-Mdir='+str(out/'csrc'), '-o', out/'simv', out/'BUFGCE.v', out/'glbl.v', out/'bank.sv',
                out/'monitor.sv', out/'snapshot.sv', out/'sources'/Path(EXIT).name,
                *(out/'sources'/Path(n).name for n in RTL)]
        compiled = run(argv, 'compile-integration')
        require(not re.search(r'Warning-\[(?:PCWM|IPDW)', compiled), 'shadow integration port/declaration mismatch')
        integration = []
        scenarios = [('healthy', [], 0), *[(f, ['+fault='+f], 0) for f in ('missing', 'ce', 'cycle', 'owner', 'lost')],
                     ('corrupt', ['+corrupt'], 1), *[('reset-'+f, ['+reset_at='+f], 0) for f in control.RESET_PHASES]]
        for name, flags, expected in scenarios:
            work = out/name
            work.mkdir()
            text = run([out/'simv', '-no_save', '+frames='+str(out/(name+'.hex')), *flags], name, expected, work)
            if name == 'corrupt':
                require('reason=banked logical CE state' in text, 'unexpected corruption failure')
            else:
                require('PHYSICAL_TRANSPORT_'+('PASS' if name == 'healthy' else 'RESET_PASS' if name.startswith('reset-') else 'REJECT') in text,
                        'incomplete underlying physical run '+name)
                m = re.search(r'SHADOW_AUDIT_PASS captures=(\d+) word_checks=(\d+) live_changes=(\d+)', text)
                require(m and int(m[1]) > 0 and int(m[2]) > 0 and int(m[3]) > 0, 'missing dynamic shadow audit '+name)
                integration.append(dict(scenario=name, captures=int(m[1]), word_checks=int(m[2]), live_changes=int(m[3])))
        # Separately compile a semantic defect in the sampling edge, not a
        # damaged receipt: one stale bit must fail at its first unequal word.
        original = (out/'snapshot.sv').read_text()
        require(original.count('saved_state <= live_state;') == 1, 'mutation boundary changed')
        mutant = out/'corrupt-snapshot.sv'
        mutant.write_text(original.replace('saved_state <= live_state;', "saved_state <= {live_state[GATES+480:1], 1'b0};"))
        work = out/'semantic-corruption'
        work.mkdir()
        run([*common, '-top', 'transport_control_snapshot_tb', '-Mdir='+str(work/'csrc'), '-o', work/'simv',
             mutant, out/'sources'/Path(TB).name, out/'sources'/Path(EXIT).name], 'compile-corruption')
        text = run([work/'simv', '-no_save'], 'semantic-corruption', 1, work)
        require('SNAPSHOT_DIVERGENCE cycle=107 signal=snapshot word word=0 captures=1' in text,
                'corruption did not fail at first differing captured word')
        waves = list(out.rglob('*.vcd'))
        require(len(waves) == 16 and all(re.search(r'^#[1-9][0-9]*$', f.read_text(), re.M) for f in waves),
                'missing or unflushed debug waveform')
        # The source moves after the captured cut. Independently preserve both
        # labels from the failed process's actual flushed debug waveform.
        codes, values = {}, {}
        for line in (work/'transport-control-snapshot.vcd').read_text().splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == '$var' and parts[4] in (
                    'snapshot_cycle', 'expected_cycle', 'target_cycle', 'word_index', 'expected'):
                codes.setdefault(parts[4], parts[3])
            elif line.startswith('b') and len(parts) == 2:
                values[parts[1]] = parts[0][1:]
        require(set(codes) == {'snapshot_cycle', 'expected_cycle', 'target_cycle', 'word_index', 'expected'},
                'incomplete negative waveform visibility')
        require(all(re.fullmatch('[01]+', values.get(code, '')) for code in codes.values()),
                'unknown or unflushed negative waveform state')
        negative = {name: int(values[code], 2) for name, code in codes.items()}
        require(negative == dict(snapshot_cycle=100, expected_cycle=100, target_cycle=107,
                                 word_index=0, expected=1), 'incorrect first-divergence cut/observation labels')
        summary.update(results=results, integration=integration, semantic_corruption_rejected=True,
                       negative_wave_labels=negative, debug_wave_count=len(waves),
                       inputs=native['inputs'], native_receipt=str(a.native/'summary.json'))
        summary['artifacts'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*')
                                if f.is_file() and f.suffix in ('.log', '.vcd', '.hex', '.sv')}
    else:
        native, eda = validate(a.native, 'f2'), validate(a.eda, 'eda')
        require(native['inputs'] == eda['inputs'] and len(eda['results']) == 3 and
                len(eda['integration']) == 11 and eda['semantic_corruption_rejected'], 'incomplete shadow evidence')
        require((a.native/'fixture.sv').read_text() == fixture(a.generated) and
                (a.native/'synth.tcl').read_text() == tcl() and
                (a.native/'monitor.sv').read_text() == monitor(a.generated), 'altered shadow contract')
        summary.update(inputs={}, artifacts={}, matched_sources=len(sources),
                       native_receipt=str(a.native/'summary.json'), eda_receipt=str(a.eda/'summary.json'))
    require(sources == {n: sha(ROOT/n) for n in SOURCES}, 'sources changed during verification')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
