"""Audit/synthesize real transport register readout; run VCS ONLY on EDA.

Live observation is not a coherent multiword checkpoint or a restore adapter.
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
from tools.checkpoint_formats.tests.verify_physical_capture_transport import RTL, TB, EXIT, RESET_PHASES

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SCALA = 'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointTransportControlState.scala'
SPEC = 'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/CheckpointTransportControlStateSpec.scala'
SELF = 'tools/checkpoint_formats/tests/verify_transport_control_state.py'
SOURCES = (*RTL, TB, EXIT, SCALA, SPEC, SELF,
           'tools/checkpoint_formats/tests/test_transport_control_state.py',
           'tools/checkpoint_formats/tests/verify_physical_capture_transport.py',
           'tools/checkpoint_formats/codec.py', 'tools/checkpoint_formats/toolchain.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def width(expr, gates):
    if expr is None:
        return 1
    match = re.fullmatch(r'(?:(GATES)\s*([+-])\s*)?(\d+)\s*:\s*0', expr.strip())
    require(match is not None, 'unrecognized state width '+expr)
    high = int(match[3])
    if match[1]:
        high = gates + high if match[2] == '+' else gates - high
    return high + 1


def reconstruct(sources, gates):
    """Reconstruct sequential storage from declarations AND procedural writes.

    In particular, procedural combinational dma_data and CRC function locals
    are not registers. A new, omitted or multiply clocked register rejects.
    """
    tables = {}
    for filename, prefix in [('CheckpointCaptureTransport.sv', 'transport'),
                             ('CheckpointCaptureCut.sv', 'transport.cut'),
                             ('CheckpointPhysicalClockCut.sv', 'physical')]:
        text = re.sub(r'//[^\n]*|/\*.*?\*/', '', sources[filename], flags=re.S)
        text = re.sub(r'function\b.*?endfunction', '', text, flags=re.S)
        declared = {}
        for match in re.finditer(r'\breg\s+(?:\[([^]]+)\]\s*)?(\w+(?:\s*,\s*\w+)*)\s*[;,)\n]', text):
            for name in re.split(r'\s*,\s*', match[2]):
                require(name not in declared, 'duplicate state declaration '+name)
                declared[name] = width(match[1], gates)
        written, writers, resets = {}, {}, {}
        blocks = list(re.finditer(r'always\s*@\s*\((posedge|negedge)\s+clock\)', text))
        for index, block in enumerate(blocks):
            end = blocks[index+1].start() if index+1 < len(blocks) else len(text)
            body = text[block.end():end]
            for name in re.findall(r'\b(\w+)\s*(?:\[[^]]+\])?\s*<=', body):
                require(name in declared, 'nonblocking write to undeclared state '+name)
                edge = block[1]+' clock'
                require(name not in writers or writers[name] == index, 'multiple state writers '+name)
                writers[name] = index
                written[name] = edge
            reset_blocks = re.findall(r'if\s*\(reset\)\s*(?:begin\b(.*?)\bend\b|([^;]+;))', body, re.S)
            for reset_body in reset_blocks:
                for name, value in re.findall(r'\b(\w+)\s*<=\s*([^;]+);', ''.join(reset_body)):
                    value = value.strip()
                    literal = re.fullmatch(r"(\d+)'([bhd])([0-9a-fA-F_]+)", value)
                    if literal:
                        parsed = int(literal[3].replace('_', ''), {'b': 2, 'h': 16, 'd': 10}[literal[2]])
                        require(parsed.bit_length() <= int(literal[1]), 'truncated reset literal')
                    elif value.isdecimal():
                        parsed = int(value)
                    else:
                        constant = re.findall(r'\b'+re.escape(value)+r'\s*=\s*(\d+)\b', text)
                        require(len(constant) == 1, 'unresolved reset constant '+value)
                        parsed = int(constant[0])
                    require(name in declared and name not in resets and parsed.bit_length() <= declared[name],
                            'ambiguous/invalid reset '+name)
                    resets[name] = parsed
        concat = re.findall(r'assign\s+control_state\s*=\s*\{([^}]+)\}\s*;', text, re.S)
        require(len(concat) == 1, 'missing/ambiguous state packing '+filename)
        order = [s.strip() for s in concat[0].split(',')][::-1]
        if prefix == 'transport':
            require(order[-1] == 'cut_control_state' and
                    '.control_state(cut_control_state)' in text, 'lost nested cut state')
            order = order[:-1]
        require(len(order) == len(written) and set(order) == set(written),
                'omitted, duplicated or nonsequential readout state '+filename)
        require(set(resets) == set(written), 'missing explicit state reset '+filename)
        tables[prefix] = [(prefix+'.'+n, declared[n], written[n], resets[n]) for n in order]
    outer = sources['CheckpointPhysicalCaptureTransport.sv']
    require(re.search(r'assign\s+control_state\s*=\s*\{physical_control_state,\s*transport_control_state\}', outer)
            and '.control_state(physical_control_state)' in outer and
            '.control_state(transport_control_state)' in outer, 'changed outer state composition')
    rows = []
    offset = 0
    for prefix in ('transport', 'transport.cut', 'physical'):
        for path, bits, edge, reset in tables[prefix]:
            rows.append(dict(relative_path=path, width=bits, offset=offset, clock=edge,
                             reset_value=reset))
            offset += bits
    return rows


def audit(generated):
    doc = json.loads((generated/'control-state.json').read_text())
    sources = {Path(n).name: (ROOT/n).read_text() for n in RTL}
    require(doc['scope'] == 'live_transport_register_observation_only' and doc['schema_version'] == 1 and
            doc['sampling_contract'] == 'live_vector_not_an_atomic_multiword_snapshot' and
            doc['external_transport_state_owner'] == 'unsupported_no_atomic_capture_restore_adapter' and
            all(doc[k] is False for k in ('includes_vendor_gate_state', 'includes_stream_host_state',
                'complete_fpga_capture', 'deployable_capture_image', 'metasim_restore_supported')), 'false ownership admission')
    require(doc['reference_sha256'] == sha(generated/'reserved.fir') and
            doc['annotations_sha256'] == sha(generated/'reserved-annotations.json'), 'stale state observation inputs')
    annotations = json.loads((generated/'reserved-annotations.json').read_text())
    for name, text in sources.items():
        inline = [a for a in annotations if a['class'] == 'firrtl.transforms.BlackBoxInlineAnno' and a['name'] == name]
        require(len(inline) == 1 and inline[0]['text'] == text and
                doc['sources'][name] == hashlib.sha256(text.encode()).hexdigest(), 'changed state implementation '+name)
    reconstructed = reconstruct(sources, doc['gates'])
    expected = [dict(r, hierarchy=doc['transport']+'.'+r['relative_path']) for r in reconstructed]
    require(expected == doc['state'] and len(expected) == 24, 'incorrect exhaustive register layout')
    require(sum(r['width'] for r in expected) == doc['bits'] == 481+doc['gates'] and
            doc['words'] == (doc['bits']+63)//64 and doc['bank_sha256'] == sha(generated/'control-state-bank.sv'),
            'truncated state readout')
    return reconstructed


def monitor(generated):
    rows = reconstruct({Path(n).name: (ROOT/n).read_text() for n in RTL}, 3)
    packed = ', '.join('dut.'+r['relative_path'] for r in rows[::-1])
    tb = (ROOT/TB).read_text().replace('.control_state(),', '.control_state(control_state),')
    require(tb.count('  wire [511:0] dma_data;') == 1, 'readout declaration boundary changed')
    tb = tb.replace('  wire [511:0] dma_data;', '  wire [511:0] dma_data;\n  wire [483:0] control_state;')
    marker = '  integer checks=0'
    require(tb.count(marker) == 1, 'monitor injection boundary changed')
    observation = f'''  reg [31:0] control_word_index=0;
  wire control_word_valid;
  wire [63:0] control_word_data;
  CheckpointTransportControlReadout control_readout(control_state, control_word_index,
      control_word_valid, control_word_data);
  integer control_samples=0, control_word_checks=0, cw;
  reg [483:0] control_expected;
  always @(posedge clock or negedge clock) begin
    #3;
    control_expected = {{{packed}}};
    if (control_state !== control_expected) begin
      $display("CONTROL_STATE_DIVERGENCE cycle=%0d sample=%0d",target_cycle,control_samples);
      checkpoint_network_fail(); $fatal(1,"state observation mismatch");
    end
    for(cw=0;cw<10;cw=cw+1) begin
      control_word_index=cw; #0.001;
      if (control_word_valid !== (cw<8) || control_word_data !==
          (cw<8 ? (control_expected >> (cw*64)) & 64'hffffffffffffffff : 64'b0)) begin
        $display("CONTROL_WORD_DIVERGENCE cycle=%0d word=%0d",target_cycle,cw);
        checkpoint_network_fail(); $fatal(1,"bank observation mismatch");
      end
      control_word_checks++;
    end
    control_samples++;
  end
  final $display("CONTROL_STATE_AUDIT_PASS samples=%0d word_checks=%0d fields=24 bits=484",control_samples,control_word_checks);
'''
    text = tb.replace(marker, observation+marker).replace('checkpoint_network_fail(); $fatal',
                '$dumpflush; #0.001; checkpoint_network_fail(); $fatal')
    require(text.count('import "DPI-C" function void checkpoint_network_fail();') == 1,
            'failure instrumentation changed the DPI declaration')
    return text


def fixture(generated):
    # Reuse exact public declarations, leaving the full protocol unconstrained
    # so synthesis cannot hide registers behind a toy descriptor ROM.
    text = (ROOT/RTL[-1]).read_text()
    start = text.index('    input wire clock, reset,')
    end = text.index('\n);', start)
    ports = text[start:end].replace('GATES+480', '483').replace('GATES-1', '2').replace('OWNERS-1', '3')
    names = []
    for line in re.sub(r'//[^\n]*', '', ports).splitlines():
        line = re.sub(r'^\s*(?:input|output) wire\s+(?:\[[^]]+\]\s*)?', '', line).strip().rstrip(',')
        if line:
            names.extend(n.strip() for n in line.split(','))
    ports += ',\n    input wire [31:0] word_index,\n    output wire word_valid,\n    output wire [63:0] word_data'
    return ('module ControlStateSynthesisFixture(\n'+ports+'\n);\n'
            '  CheckpointPhysicalCaptureTransport #(.GATES(3),.OWNERS(4),.ENTRIES(3),\n'
            '    .EXTERNAL_CLOCK_NETWORK(1),.MANIFEST_SHA256(256\'h1234)) dut(\n'+
            ',\n'.join('    .'+n+'('+n+')' for n in names)+');\n'
            '  CheckpointTransportControlReadout bank(control_state,word_index,word_valid,word_data);\nendmodule\n')


def tcl():
    rows = reconstruct({Path(n).name: (ROOT/n).read_text() for n in RTL}, 3)
    fields = ' '.join('{'+r['relative_path'].replace('.', '/')+' '+str(r['width'])+' '+str(r['offset'])+'}' for r in rows)
    return '''set_param general.maxThreads 4
read_verilog -sv sources/CheckpointCaptureCut.sv sources/CheckpointCaptureTransport.sv sources/CheckpointPhysicalClockCut.sv sources/CheckpointPhysicalCaptureTransport.sv bank.sv fixture.sv
synth_design -top ControlStateSynthesisFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set raw [get_nets -of_objects [get_ports clock]]
set regs [get_cells -hier -filter {REF_NAME =~ FD*}]
set falling 0
foreach cell $regs {
  set clock_pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[llength $clock_pin] != 1 || [lsearch -exact [get_nets -segments -of_objects $clock_pin] $raw] < 0} {error "state lost raw clock $cell"}
  set inverted [get_property IS_INVERTED $clock_pin]
  if {$inverted ni {0 1}} {error "unresolved state clock polarity $cell"}
  if {$inverted} {
    if {$cell ne "dut/physical/freeze_low_reg"} {error "unexpected falling-edge state $cell"}
    incr falling
  }
}
if {$falling != 1} {error "missing falling-edge physical mask"}
set fd [open state-registers.tsv w]
set observed {}
set bf [open state-bits.tsv w]
foreach row {'''+fields+'''} {
  lassign $row field width offset
  set selected [get_cells -hier -filter "NAME =~ dut/${field}_reg* && REF_NAME =~ FD*"]
  if {[llength $selected] != $width} {error "changed physical width $field expected=$width actual=[llength $selected]"}
  foreach cell $selected {
    if {[lsearch -exact $observed $cell] >= 0} {error "ambiguous state field $cell"}
    if {[get_property FSM_ENCODED_STATES $cell] ne ""} {error "unmapped encoded state $cell"}
    set bit 0
    if {$width > 1} {
      if {![regexp {\\[([0-9]+)\\]$} $cell unused bit] || $bit >= $width} {error "unbound physical bit $cell"}
    }
    set index [expr {$offset+$bit}]
    set port [get_ports [format {control_state[%d]} $index]]
    set q [get_pins -of_objects $cell -filter {REF_PIN_NAME == Q}]
    if {[llength $port] != 1 || [llength $q] != 1 ||
        [lsort [get_nets -segments -of_objects $port]] ne [lsort [get_nets -segments -of_objects $q]]} {
      error "physical Q differs from exported source bit $cell index=$index"
    }
    puts $bf "$field\t$bit\t$index\t$cell\t$q\t$port"
    lappend observed $cell
  }
  puts $fd "$field\t[llength $selected]"
}
close $fd
close $bf
set ef [open state-native-encodings.tsv w]
puts $ef "policy=source_encoding_only expected_encoded_registers=0"
set encoded 0
foreach cell $regs {
  set encoding [get_property FSM_ENCODED_STATES $cell]
  if {$encoding ne ""} {
    incr encoded
    puts $ef "$cell\t[get_property REF_NAME $cell]\t[get_property FILE_NAME $cell]\t[get_property LINE_NUMBER $cell]\t$encoding"
  }
}
close $ef
if {$encoded != 0} {error "unmapped native FSM encoding"}
if {[lsort $observed] ne [lsort $regs]} {error "unclassified sequential state"}
if {[llength $regs] != 484} {error "source/native state width mismatch"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force control-state.dcp
write_verilog -force -mode funcsim control-state-netlist.v
puts "CONTROL_STATE_SYNTH_PASS fields=24 live_bits=484 raw_registers=[llength $regs] falling=1"
puts "CONTROL_STATE_NATIVE_ENCODING registers=$encoded atomic_capture_restore_adapter=UNSUPPORTED"
'''


def audit_native(directory):
    """Check the emitted physical-bit partition, independently of Tcl counts."""
    rows = reconstruct({Path(n).name: (ROOT/n).read_text() for n in RTL}, 3)
    expected = {}
    for row in rows:
        field = row['relative_path'].replace('.', '/')
        for bit in range(row['width']):
            cell = 'dut/'+field+'_reg'+('['+str(bit)+']' if row['width'] > 1 else '')
            expected[row['offset']+bit] = (field, bit, cell)
    actual = {}
    for line in (directory/'state-bits.tsv').read_text().splitlines():
        field, bit, index, cell, q, port = line.split('\t')
        bit, index = int(bit), int(index)
        require(index not in actual and expected.get(index) == (field, bit, cell) and
                q == cell+'/Q' and port == 'control_state['+str(index)+']',
                'incorrect/duplicate physical state bit '+line)
        actual[index] = (field, bit, cell)
    require(actual == expected and len(actual) == 484, 'incomplete physical state bit mapping')
    field_rows = [line.split('\t') for line in (directory/'state-registers.tsv').read_text().splitlines()]
    fields = dict(field_rows)
    require(len(field_rows) == len(fields) == len(rows) and
            fields == {r['relative_path'].replace('.', '/'): str(r['width']) for r in rows},
            'incorrect physical state field widths')
    require((directory/'state-native-encodings.tsv').read_text() ==
            'policy=source_encoding_only expected_encoded_registers=0\n', 'native encoded storage remains')
    return len(actual)


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
    audit(a.generated)
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
                doc['physical_fpga_capture'] is False and doc['atomic_transport_owner'] is False, 'stale/false receipt')
        for group in ('inputs', 'artifacts'):
            for name, digest in doc[group].items():
                require(sha(directory/name) == digest, 'changed evidence '+name)
        if backend == 'f2':
            audit_native(directory)
        return doc

    summary = dict(status='pass', backend='eda' if a.mode == 'vcs' else 'f2', sources=sources,
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='exhaustive live control register observation component only',
                   physical_fpga_capture=False, atomic_transport_owner=False)
    if a.mode == 'vivado':
        require(str(ROOT) == '/home/ubuntu/chia-cy-checkpoint-restore' and shutil.which('vivado'), 'native Vivado required')
        for name in RTL:
            dst = out/'sources'/Path(name).name
            dst.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT/name, dst)
        shutil.copyfile(a.generated/'control-state-bank-3.sv', out/'bank.sv')
        (out/'fixture.sv').write_text(fixture(a.generated))
        (out/'synth.tcl').write_text(tcl())
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for name, src in [('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')]:
            shutil.copyfile(src, out/name)
        (out/'monitor.sv').write_text(monitor(a.generated))
        shutil.copyfile(ROOT/EXIT, out/Path(EXIT).name)
        summary['inputs'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*') if f.is_file()}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require(re.search(r'CONTROL_STATE_SYNTH_PASS fields=24 live_bits=484 raw_registers=484 falling=1', text)
                and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'incomplete state synthesis')
        summary['mapped_physical_bits'] = audit_native(out)
        # Re-enable inference in each actual controller separately. The same
        # physical/Q audit must reject extra or recoded storage; merely seeing
        # the RTL attribute is not evidence that synthesis honored it.
        negative = []
        for name in ('CheckpointCaptureCut.sv', 'CheckpointCaptureTransport.sv'):
            work = out/('inferred-'+Path(name).stem)
            work.mkdir()
            shutil.copytree(out/'sources', work/'sources')
            for filename in ('bank.sv', 'fixture.sv', 'synth.tcl'):
                shutil.copyfile(out/filename, work/filename)
            path = work/'sources'/name
            original = path.read_text()
            attribute = '(* fsm_encoding = "none" *) '
            require(original.count(attribute) == 1, 'encoding policy mutation site changed')
            path.write_text(original.replace(attribute, ''))
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'],
                       'inferred-'+Path(name).stem, expected=1, cwd=work)
            require(re.search(r'changed physical width|unmapped encoded state|unmapped native FSM encoding', text)
                    and 'CONTROL_STATE_SYNTH_PASS' not in text, 'inference defect rejected for unrelated reason')
            negative.append(dict(source=name, rejected=True, returncode=1))
        work = out/'swapped-export'
        work.mkdir()
        shutil.copytree(out/'sources', work/'sources')
        for filename in ('bank.sv', 'fixture.sv', 'synth.tcl'):
            shutil.copyfile(out/filename, work/filename)
        path = work/'fixture.sv'
        original = path.read_text()
        require(original.count('.control_state(control_state)') == 1, 'physical export mutation site changed')
        path.write_text(original.replace('.control_state(control_state)', '.control_state(raw_state)').replace(
            '  CheckpointPhysicalCaptureTransport #(', '''  wire [483:0] raw_state;
  assign control_state = {raw_state[483:8],raw_state[3:0],raw_state[7:4]};
  CheckpointPhysicalCaptureTransport #('''))
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'swapped-export', expected=1, cwd=work)
        require('physical Q differs from exported source bit' in text and 'CONTROL_STATE_SYNTH_PASS' not in text,
                'physical export defect rejected for unrelated reason')
        negative.append(dict(source='fixture.sv', rejected=True, returncode=1))
        summary['native_state_negatives'] = negative
        summary['artifacts'] = {n: sha(out/n) for n in ('synth.log', 'state-registers.tsv', 'state-bits.tsv', 'state-native-encodings.tsv', 'control-state.dcp',
            'control-state-netlist.v', 'utilization.rpt', 'timing.rpt', 'commands.json',
            'inferred-CheckpointCaptureCut.log', 'inferred-CheckpointCaptureTransport.log', 'swapped-export.log')}
        summary['artifacts'].update({str(f.relative_to(out)): sha(f) for f in out.rglob('*')
            if f.is_file() and (any(p.name.startswith('inferred-') or p.name == 'swapped-export'
                                  for p in f.relative_to(out).parents)) and
            f.suffix in ('.log', '.sv', '.tcl', '.tsv')})
    elif a.mode == 'vcs':
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA SP2 VCS required')
        native = validate(a.native, 'f2')
        for name in native['inputs']:
            dst = out/name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(a.native/name, dst)
        argv = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                '-top', 'physical_capture_transport_tb', '-top', 'glbl', '-Mdir='+str(out/'csrc'), '-o', out/'simv',
                out/'BUFGCE.v', out/'glbl.v', out/'bank.sv', out/'monitor.sv', out/Path(EXIT).name,
                *(out/'sources'/Path(n).name for n in RTL)]
        compiled = run(argv, 'compile')
        require(not re.search(r'Warning-\[(?:PCWM|IPDW)', compiled), 'state readout port/declaration mismatch')
        results = []
        scenarios = [('healthy', [], 0), *[(f, ['+fault='+f], 0) for f in ('missing', 'ce', 'cycle', 'owner', 'lost')],
                     ('corrupt', ['+corrupt'], 1), *[('reset-'+f, ['+reset_at='+f], 0) for f in RESET_PHASES]]
        for name, flags, expected in scenarios:
            work = out/name
            work.mkdir()
            text = run([out/'simv', '-no_save', '+frames='+str(out/(name+'.hex')), *flags], name, expected, work)
            if name == 'corrupt':
                require('reason=banked logical CE state' in text, 'unexpected deliberate corruption failure')
            else:
                require('PHYSICAL_TRANSPORT_'+('PASS' if name == 'healthy' else 'RESET_PASS' if name.startswith('reset-') else 'REJECT') in text,
                        'incomplete underlying physical run '+name)
                matched = re.search(r'CONTROL_STATE_AUDIT_PASS samples=(\d+) word_checks=(\d+) fields=24 bits=484', text)
                require(matched and int(matched[1]) > 0 and int(matched[2]) == 10*int(matched[1]), 'missing control audit '+name)
                results.append(dict(scenario=name, samples=int(matched[1]), word_checks=int(matched[2])))
        # Miswire equal-width fields in actual RTL: the independent hierarchy
        # oracle must detect the first differing sample, even with new hashes.
        path = out/'sources/CheckpointCaptureTransport.sv'
        original = path.read_text()
        require(original.count('outstanding, stream_crc, words, saved_data,') == 1, 'corruption site changed')
        mutant = out/'swapped-CheckpointCaptureTransport.sv'
        mutant.write_text(original.replace('outstanding, stream_crc, words, saved_data,',
                                            'outstanding, stream_crc, saved_data, words,'))
        faulty = [mutant if v == path else out/'simv-swapped' if v == out/'simv' else
                  '-Mdir='+str(out/'csrc-swapped') if str(v).startswith('-Mdir=') else v for v in argv]
        run(faulty, 'compile-swapped')
        work = out/'swapped'
        work.mkdir()
        text = run([out/'simv-swapped', '-no_save'], 'swapped', 1, work)
        require('CONTROL_STATE_DIVERGENCE' in text, 'swapped state did not diverge')
        waves = list(out.rglob('*.vcd'))
        require(len(waves) == 13 and all(re.search(r'^#[1-9][0-9]*$', f.read_text(), re.M) for f in waves),
                'missing or unflushed readout debug waveform')
        summary.update(results=results, semantic_miswire_rejected=True, inputs=native['inputs'],
                       native_receipt=str(a.native/'summary.json'))
        summary['artifacts'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*')
                                if f.is_file() and f.suffix in ('.log', '.vcd', '.hex', '.sv')}
    else:
        native, eda = validate(a.native, 'f2'), validate(a.eda, 'eda')
        require(native['inputs'] == eda['inputs'] and len(eda['results']) == 11 and
                eda['semantic_miswire_rejected'] and len(native['native_state_negatives']) == 3,
                'incomplete native/EDA comparison')
        require((a.native/'fixture.sv').read_text() == fixture(a.generated) and
                (a.native/'synth.tcl').read_text() == tcl() and
                (a.native/'monitor.sv').read_text() == monitor(a.generated), 'altered native/EDA contract')
        summary.update(inputs={}, artifacts={}, matched_inputs=len(native['inputs']), matched_sources=len(sources),
                       native_receipt=str(a.native/'summary.json'), eda_receipt=str(a.eda/'summary.json'))
    require(sources == {n: sha(ROOT/n) for n in SOURCES}, 'sources changed during verification')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
