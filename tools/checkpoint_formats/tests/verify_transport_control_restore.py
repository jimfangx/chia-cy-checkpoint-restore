"""Transactional transport restore staging: localhost Vivado / EDA-only VCS.

No production owner, physical restore mux or FPGA capture is admitted.
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

ROOT, RUNS = control.ROOT, control.RUNS
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointTransportControlRestore.sv'
TB = 'tools/checkpoint_formats/tests/transport_control_restore_tb.sv'
SELF = 'tools/checkpoint_formats/tests/verify_transport_control_restore.py'
SOURCES = (*control.SOURCES, RTL, TB, SELF)
SCHEMA = '96c729e8745f16d1'  # Diagnostic fixture identity only, never a production build.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def synthesis_tcl():
    return '''read_verilog -sv restore.sv
synth_design -top CheckpointTransportControlRestore -part xcvu47p-fsvh2892-2L-e -mode out_of_context -generic GATES=3 -generic SCHEMA_SHA256=256'h96c729e8745f16d1
create_clock -name raw -period 7.142857 [get_ports clock]
set raw [get_nets -of_objects [get_ports clock]]
set report [open storage.tsv w]
set classified {}
foreach {field width} {state 2 saved_state 484 saved_cycle 64 saved_crc 32 running_crc 32 next_word 32 applied 1 error 8} {
  set regs [get_cells -hier -filter "NAME =~ ${field}_reg* && REF_NAME =~ FD*"]
  if {[llength $regs] != $width} {error "incorrect staging field $field expected=$width actual=[llength $regs]"}
  foreach cell $regs {
    set pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[llength $pin] != 1 || [get_property IS_INVERTED $pin] != 0 ||
        [lsearch -exact [get_nets -segments -of_objects $pin] $raw] < 0} {error "lost staging raw positive edge $cell"}
    if {[get_property FSM_ENCODED_STATES $cell] ne ""} {error "unmapped staging FSM state $cell"}
    lappend classified $cell
    puts $report "$field\t$cell\t[get_property REF_NAME $cell]"
  }
}
close $report
set sequential [get_cells -hier -filter {IS_SEQUENTIAL == 1}]
if {[lsort $sequential] ne [lsort $classified]} {error "unclassified staging sequential storage"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force restore.dcp
write_verilog -force restore-netlist.v
puts "RESTORE_SYNTH_PASS fields=8 registers=[llength $sequential] raw_positive_edge=1"
'''


def audit_storage(directory):
    rows = [line.split('\t') for line in (directory/'storage.tsv').read_text().splitlines()]
    expected = dict(state=2, saved_state=484, saved_cycle=64, saved_crc=32,
                    running_crc=32, next_word=32, applied=1, error=8)
    require(len(rows) == sum(expected.values()) == 655 and len({r[1] for r in rows}) == 655,
            'lost/aliased native staging storage')
    for field, width in expected.items():
        selected = [r for r in rows if r[0] == field]
        names = {field+'_reg' if width == 1 else f'{field}_reg[{i}]' for i in range(width)}
        require(len(selected) == width and {r[1] for r in selected} == names and
                all(r[2] in ('FDRE', 'FDSE') for r in selected), 'changed field '+field)
    return len(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['vivado', 'vcs', 'audit'], required=True)
    p.add_argument('--generated', type=Path, required=True)
    p.add_argument('--native', type=Path)
    p.add_argument('--eda', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS), 'all evidence belongs below runs')
    a.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=a.mode+'-', dir=a.out.resolve()))
    control.audit(a.generated)
    sources = {n: sha(ROOT/n) for n in SOURCES}
    summary = dict(status='pass', backend='eda' if a.mode == 'vcs' else 'f2',
                   scope='transactional transport restore staging component only',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), sources=sources, physical_fpga_capture=False,
                   production_transport_owner=False, physical_restore_adapter=False)
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
        require(directory is not None, 'missing '+backend+' evidence')
        doc = json.loads((directory/'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and doc['sources'] == sources and
                not any(doc[n] for n in ('physical_fpga_capture', 'production_transport_owner',
                                        'physical_restore_adapter')), 'stale or false restore receipt')
        for group in ('inputs', 'artifacts'):
            for name, digest in doc[group].items():
                require(sha(directory/name) == digest, 'changed evidence '+name)
        if backend == 'f2':
            require(audit_storage(directory) == doc['registers'], 'native census mismatch')
        return doc

    if a.mode == 'vivado':
        require(str(ROOT) == '/home/ubuntu/chia-cy-checkpoint-restore' and shutil.which('vivado'),
                'native localhost Vivado required')
        for name, src in [('restore.sv', ROOT/RTL), ('tb.sv', ROOT/TB),
                          ('exit.cc', ROOT/control.EXIT), ('control-state.json', a.generated/'control-state.json')]:
            shutil.copyfile(src, out/name)
        (out/'synth.tcl').write_text(synthesis_tcl())
        summary['inputs'] = {str(f.relative_to(out)): sha(f) for f in out.iterdir() if f.is_file()}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require('RESTORE_SYNTH_PASS fields=8 registers=655 raw_positive_edge=1' in text and
                not re.search(r'ERROR:|CRITICAL WARNING:', text), 'incomplete native restore synthesis')
        summary['registers'] = audit_storage(out)
        summary['artifacts'] = {n: sha(out/n) for n in ('storage.tsv', 'synth.log', 'restore.dcp',
            'restore-netlist.v', 'utilization.rpt', 'timing.rpt', 'commands.json')}
    elif a.mode == 'vcs':
        require(str(ROOT) == '/scratch/jfx/chia-cy-checkpoint-restore' and
                os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(),
                'EDA native SP2 VCS required')
        native = validate(a.native, 'f2')
        for name in native['inputs']:
            shutil.copyfile(a.native/name, out/name)
        common = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all']
        results = []
        for gates, schema_zero in [(1, False), (3, False), (31, False), (65, False), (0, False), (65536, False), (3, True)]:
            name = f'gates-{gates}'+('-schema-zero' if schema_zero else '')
            work = out/name
            work.mkdir()
            flags = ['+define+RESTORE_GATES='+str(gates)]
            if schema_zero:
                flags.append('+define+RESTORE_SCHEMA=256\'h0')
            text = run([*common, *flags, '-top', 'transport_control_restore_tb', '-Mdir='+str(work/'csrc'),
                        '-o', work/'simv', out/'restore.sv', out/'tb.sv', out/'exit.cc'], 'compile-'+name)
            require(not re.search(r'Warning-\[(?:PCWM|IPDW)', text), 'port/declaration mismatch')
            text = run([work/'simv', '-no_save'], name, cwd=work)
            if gates in (0, 65536) or schema_zero:
                require('RESTORE_SPECIALIZATION_REJECT' in text, 'missing invalid-specialization rejection')
                results.append(dict(gates=gates, zero_schema=schema_zero, specialization_rejected=True))
            else:
                m = re.search(r'RESTORE_PASS gates=(\d+) bits=(\d+) restores=(\d+) rejections=(\d+) checks=(\d+) acks=(\d+)', text)
                require(m and int(m[1]) == gates and int(m[2]) == 481+gates and
                        int(m[3]) == 481+gates+17 and int(m[4]) == (39 if (481+gates)%64 == 0 else 40) and
                        int(m[6]) == int(m[3])+1,
                        'incomplete restore coverage '+name)
                results.append(dict(gates=gates, restores=int(m[3]), rejections=int(m[4]),
                                    checks=int(m[5]), acknowledgements=int(m[6])))
        # Defect in real synthesized staging assignment: CRC logic is unchanged.
        # The independent oracle must stop at first offered data, before apply.
        text = (out/'restore.sv').read_text()
        marker = 'saved_state <= saved_state | ({{(BITS-64){1\'b0}},word_data} << (word_index*64));'
        require(text.count(marker) == 1, 'semantic mutation boundary changed')
        (out/'corrupt.sv').write_text(text.replace(marker, marker.replace('word_data}', "(word_data ^ 64'h1)}")))
        work = out/'semantic-corruption'
        work.mkdir()
        run([*common, '-top', 'transport_control_restore_tb', '-Mdir='+str(work/'csrc'), '-o', work/'simv',
             out/'corrupt.sv', out/'tb.sv', out/'exit.cc'], 'compile-corruption')
        text = run([work/'simv', '-no_save'], 'semantic-corruption', expected=1, cwd=work)
        require('RESTORE_DIVERGENCE cut=100 signal=apply word word=0 restores=0 acks=0' in text,
                'semantic defect did not stop before first acknowledgement')
        waves = list(out.rglob('*.vcd'))
        require(len(waves) == 8 and all(re.search(r'^#[1-9][0-9]*$', f.read_text(), re.M) for f in waves),
                'missing or unflushed debug waves')
        summary.update(results=results, semantic_corruption_rejected=True, debug_wave_count=8,
                       inputs=native['inputs'], native_receipt=str(a.native/'summary.json'))
        summary['artifacts'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*')
                                if f.is_file() and f.suffix in ('.log', '.vcd', '.sv', '.json')}
    else:
        native, eda = validate(a.native, 'f2'), validate(a.eda, 'eda')
        require(native['inputs'] == eda['inputs'] and len(eda['results']) == 7 and
                eda['semantic_corruption_rejected'] and eda['debug_wave_count'] == 8,
                'incomplete cross-backend evidence')
        require((a.native/'synth.tcl').read_text() == synthesis_tcl() and
                (a.native/'restore.sv').read_bytes() == (ROOT/RTL).read_bytes() and
                (a.native/'tb.sv').read_bytes() == (ROOT/TB).read_bytes(), 'changed restore contract')
        summary.update(inputs={}, artifacts={}, matched_sources=len(sources),
                       native_receipt=str(a.native/'summary.json'), eda_receipt=str(a.eda/'summary.json'))
    require(sources == {n: sha(ROOT/n) for n in SOURCES}, 'source changed during verification')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
