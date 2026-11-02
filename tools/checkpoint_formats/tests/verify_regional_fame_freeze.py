"""Qualify source-bound regional FAME banking on native Vivado and EDA VCS.

This small compiler fixture grants no production cut, image or CPU acceptance.
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
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'


def bench(directory):
    modules = parse_modules((directory / 'instrumented.fir').read_text())
    original = parse_modules((directory / 'host.fir').read_text())
    ports = modules['Top']['ports']
    old_ports = original['Top']['ports']
    inputs, outputs = {}, {}
    lines = ['`timescale 1ns/1ps', 'module regional_fame_freeze_tb;',
             'import "DPI-C" function void checkpoint_widget_failed();']
    for name, (direction, kind) in ports.items():
        match = re.fullmatch(r'UInt<(\d+)>', kind)
        width = 1 if kind == 'Clock' else int(match[1]) if match else 0
        require(width > 0, 'unsupported fixture port ' + name)
        shape = '' if width == 1 else f'[{width-1}:0] '
        if direction == 'input':
            inputs[name] = width
            value = 1 if name == 'hostReset' or name.endswith('ckpt_reset') else 0
            lines.append(f'reg {shape}{name}={width}\'d{value};')
        else:
            outputs[name] = width
            lines.append(f'wire {shape}{name};')
            if name in old_ports:
                lines.append(f'wire {shape}ref_{name};')
    lines += ['reg reference_clock=0;', 'Top dut(.*);']
    connections = []
    for name, (direction, _) in old_ports.items():
        value = 'reference_clock' if name == 'hostClock' else 'ref_' + name if direction == 'output' else name
        connections.append(f'.{name}({value})')
    lines += ['ReferenceTop original(' + ','.join(connections) + ');',
              'integer checks=0, steps=0, cuts=0, reads=0, host_step=0, stalls=0;',
              'task check(input bit okay,input string reason); checks++; if(!okay) begin',
              '$display("REGIONAL_FAME_DIVERGENCE host_step=%0d acknowledged=%0d signal=%s",host_step,reads,reason);',
              'checkpoint_widget_failed(); $finish; end endtask', 'task compare;']
    for name in sorted(outputs.keys() & old_ports.keys()):
        lines.append(f'check({name}===ref_{name},"boundary_{name}");')
    lines += ['endtask', 'task tick(input bit advance);',
              'hostClock=0;reference_clock=0;#3;hostClock=1;if(advance)reference_clock=1;#3;',
              'compare();hostClock=0;reference_clock=0;#3;endtask']
    prefixes = [n.removesuffix('ckpt_bank') for n in inputs if n.endswith('ckpt_bank')]
    require(len(prefixes) == 1, 'one concrete bank fixture required')
    p = prefixes[0]
    lines += ['task readword(input [7:0] bank,input [15:0] slot,input [31:0] address,input [63:0] expected);',
              f'{p}ckpt_bank=bank;{p}ckpt_slot=slot;{p}ckpt_address=address;{p}ckpt_req_valid=1;#2;',
              f'check(!$isunknown(expected),"known_original_word");',
              f'check({p}ckpt_req_ready,"request_ready");tick(0);{p}ckpt_req_valid=0;#1;',
              f'check({p}ckpt_resp_valid,"response_valid");',
              'repeat(3)begin',
              f'check({p}ckpt_resp_valid&&!{p}ckpt_resp_error&&{p}ckpt_resp_data===expected,"held_bank_word");',
              'tick(0);stalls++;end',
              f'check({p}ckpt_resp_data===expected&&!{p}ckpt_resp_error,"bank_word_before_ack");',
              f'{p}ckpt_resp_ready=1;tick(0);reads++;{p}ckpt_resp_ready=0;#1;',
              f'check(!{p}ckpt_resp_valid,"response_drained");endtask', 'task cut;']
    masks = [n for n in inputs if n.endswith('checkpoint_physical_mask')]
    require(len(masks) == 1, 'one original root-mask interface required')
    lines += [f'{masks[0]}=1;{p}ckpt_freeze=1;#3;tick(0);']
    rows = json.loads((directory / 'descriptors.json').read_text())['state']
    functional = [r for r in rows if r['domain'] == 'functional']
    require(functional, 'no functional bank entries')
    for row in functional:
        logical = row['logical_state']
        require(logical['kind'] == 'register' and logical['depth'] == 1 and logical['width'] <= 64,
                'fixture requires bounded complete scalar storage')
        name = logical['hierarchy'].replace('Top.', 'original.', 1)
        lines.append(f'readword(8\'d{row["bank"]},16\'d{row["slot"]},0,64\'({name}));')
    lines += [f'{p}ckpt_freeze=0;{masks[0]}=0;#3;cuts++;endtask', 'initial begin',
              '$dumpfile("regional-fame.vcd");$dumpvars(0,regional_fame_freeze_tb);',
              '#120;repeat(4)tick(1);hostReset=0;']
    for name in inputs:
        if name.endswith('ckpt_reset'):
            lines.append(f'{name}=0;')
    # This fixture is produced by the real FAME transform, including pending
    # clock flags and independent channel-fire state, rather than handwritten RTL.
    for suffix in ('clocks_sink_valid', 'data_sink_valid', 'value_source_ready', 'slow_source_ready'):
        require(any(n.endswith(suffix) for n in inputs), 'missing FAME channel ' + suffix)
    for name in inputs:
        if name.endswith(('clocks_sink_valid', 'clocks_sink_bits_A', 'clocks_sink_bits_B',
                          'data_sink_valid', 'value_source_ready', 'slow_source_ready')):
            lines.append(f'{name}=1;')
    lines += ['repeat(12)tick(1);', 'for(integer i=0;i<512;i++)begin host_step=i+1;']
    for name in inputs:
        if name.endswith('clocks_sink_valid'):
            lines.append(f'{name}=(i%11!=3&&i%11!=4);')
        elif name.endswith('clocks_sink_bits_A'):
            lines.append(f'{name}=(i%4!=1);')
        elif name.endswith('clocks_sink_bits_B'):
            lines.append(f'{name}=(i%3==0);')
        elif name.endswith('data_sink_valid'):
            lines.append(f'{name}=(i%7!=2);')
        elif name.endswith('data_sink_bits'):
            lines.append(f'{name}=i*6+2;')
        elif name.endswith('value_source_ready'):
            lines.append(f'{name}=(i%9!=5&&i%9!=6);')
        elif name.endswith('slow_source_ready'):
            lines.append(f'{name}=(i%13!=6);')
    lines += ['tick(1);steps++;if(i==36||i==122||i==300||i==499)cut();end',
              f'check(cuts==4&&reads=={4*len(functional)}&&stalls=={12*len(functional)},"complete_scope");',
              '$display("REGIONAL_FAME_PASS steps=%0d cuts=%0d reads=%0d stalls=%0d checks=%0d",steps,cuts,reads,stalls,checks);',
              '$finish;end endmodule']
    return '\n'.join(lines) + '\n', len(functional)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('vivado', 'vcs'))
    parser.add_argument('--generated', required=True, type=Path)
    parser.add_argument('--compiler-receipt', required=True, type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    base, generated, compiler = (local(ROOT, p).resolve() for p in
                                (args.out, args.generated, args.compiler_receipt))
    require(all(p.is_relative_to(RUNS) for p in (base, generated, compiler)), 'evidence must stay under runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    source_paths = list((ROOT / 'sims/firesim/sim/midas/src/main/scala/midas/checkpoint').glob('*.scala'))
    source_paths += [ROOT / 'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/FAMEClockProgressSpec.scala',
                     Path(__file__), ROOT / 'tools/checkpoint_formats/tests/audit_regional_fame_freeze.py',
                     ROOT / 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc']
    source_paths += [ROOT / 'tools/checkpoint_formats' / name for name in
                     ('codec.py', 'evidence.py', 'regression_runner.py', 'toolchain.py',
                      'tests/audit_physical_clock_plan.py', 'tests/audit_native_fame_progress.py',
                      'tests/test_regional_fame_freeze_audit.py')]
    sources = {str(p.relative_to(ROOT)): file_sha(p) for p in source_paths}
    names = ('host.fir', 'host-annotations.json', 'host.sv', 'instrumented.fir',
             'instrumented-annotations.json', 'instrumented.sv', 'binding.json', 'targets.json', 'descriptors.json')
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT), sources=sources,
               scope='regional FAME compiler/bank component only', physical_fpga_capture=False,
               deployable_capture_image=False, cpu_migration_verified=False,
               generated_path=str(generated), generated={n: file_sha(generated / n) for n in names}, commands=[])

    def run(argv, name, work=out, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log ' + str(log))
        return log.read_text()

    try:
        c = json.loads(compiler.read_text())
        require(c['status'] == 'pass' and c['backend'] == 'f2' and c['returncode'] == 0, 'passing compiler receipt required')
        for n, h in c['sources'].items():
            require(file_sha(local(ROOT, n)) == h, 'compiler source changed: ' + n)
        for n in names:
            require(c['artifacts'][str((generated / n).relative_to(compiler.parent))] == file_sha(generated / n),
                    'generated fixture not bound to compiler ' + n)
        doc['compiler_receipt'] = dict(path=str(compiler), sha256=file_sha(compiler))
        shutil.copytree(generated, out / 'generated')
        from tools.checkpoint_formats.tests.audit_regional_fame_freeze import audit, mutation_probes
        doc['freeze_audit'] = audit(out / 'generated')
        doc['rejected_mutations'] = mutation_probes(out / 'generated')
        for n in ('host.sv', 'instrumented.sv'):
            shutil.copyfile(generated / n, out / n)
        code, count = bench(out / 'generated')
        (out / 'regional_fame_freeze_tb.sv').write_text(code)
        doc['functional_entries'] = count
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'Vivado runs only on this manager')
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
            for name, src in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
                shutil.copyfile(src, out / name)
            (out / 'synth.tcl').write_text('''set_param general.maxThreads 4
read_verilog -sv instrumented.sv
synth_design -top Top -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports hostClock]
set observers [get_cells -hier -filter {NAME =~ *checkpoint_fame* && IS_SEQUENTIAL == 1}]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $observers] != 321 || [llength $gates] != 3} {error "incomplete original FAME storage or native clocks"}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
write_checkpoint -force synthesized.dcp
puts "REGIONAL_FAME_SYNTH_PASS observer_bits=321 gates=3"
''')
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'native')
            require('REGIONAL_FAME_SYNTH_PASS observer_bits=321 gates=3' in text and
                    not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native qualification incomplete')
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and
                    toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 required')
            native = local(ROOT, args.native).resolve()
            n = json.loads((native / 'summary.json').read_text())
            require(n['status'] == 'pass' and n['backend'] == 'f2' and n['sources'] == sources and
                    n['generated'] == doc['generated'], 'stale native provenance')
            for name, h in n['artifacts'].items():
                require(file_sha(native / name) == h, 'native evidence changed ' + name)
            doc['native_receipt'] = dict(path=str(native / 'summary.json'), sha256=file_sha(native / 'summary.json'))
            for name in ('BUFGCE.v', 'glbl.v'):
                shutil.copyfile(native / name, out / name)
            reference = (out / 'host.sv').read_text()
            for name, module in parse_modules((generated / 'host.fir').read_text()).items():
                if module['kind'] == 'module':
                    reference = re.sub(r'\b' + re.escape(name) + r'\b', 'Reference' + name, reference)
            (out / 'reference.sv').write_text(reference)
            # The corruption is compiled into the generated bank, never injected
            # with a simulator write. The bad response must stop before its ack.
            rtl = (out / 'instrumented.sv').read_text()
            marker = 'assign ckpt_resp_data = ckpt_saved_data;'
            require(marker in rtl, 'missing actual bank response equation')
            (out / 'corrupt.sv').write_text(rtl.replace(marker, 'assign ckpt_resp_data = ckpt_saved_data ^ 64\'h1;', 1))
            doc['cases'] = {}
            for case in ('healthy', 'corrupt'):
                binary = out / ('simv-' + case)
                run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                     '-top', 'regional_fame_freeze_tb', '-top', 'glbl', '-Mdir=' + str(out / ('csrc-' + case)),
                     '-o', binary, out / ('instrumented.sv' if case == 'healthy' else 'corrupt.sv'),
                     out / 'reference.sv', out / 'BUFGCE.v', out / 'glbl.v', out / 'regional_fame_freeze_tb.sv',
                     ROOT / 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc', '-CFLAGS', '-std=c++17'], case + '-compile')
                work = out / case
                work.mkdir()
                text = run([binary, '-no_save'], case, work, 0 if case == 'healthy' else 1)
                expected = f'REGIONAL_FAME_PASS steps=512 cuts=4 reads={count*4} stalls={count*12}'
                require(expected in text if case == 'healthy' else
                        'REGIONAL_FAME_DIVERGENCE host_step=37 acknowledged=0 signal=held_bank_word' in text,
                        'incomplete scope or divergent response acknowledged')
                wave = work / 'regional-fame.vcd'
                require(wave.stat().st_size > 1000, 'missing full debug waveform')
                doc['cases'][case] = dict(log=str(out / (case + '.log')), waveform=str(wave))
        require(sources == {n: file_sha(ROOT / n) for n in sources}, 'source changed during execution')
        doc['status'] = 'pass'
    except Exception as error:
        doc['error'] = str(error)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): file_sha(p) for p in out.rglob('*') if p.is_file() and
                            p.suffix in {'.sv', '.v', '.fir', '.json', '.log', '.rpt', '.tcl', '.dcp', '.vcd'}}
        receipt = out / 'summary.json'
        receipt.write_text(json.dumps(doc, indent=2) + '\n')
        print(receipt, flush=True)


if __name__ == '__main__':
    main()
