"""Qualify concrete live register snapshots on localhost Vivado and EDA SP2.

The actual Rocket reorder-queue component is exercised with outstanding tags;
this is not a global cut, deployed image or hardware CPU capture receipt.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_register_snapshot import audit, audit_reference, bind_reference_receipt, sha, PREFIX, OBS, ADAPTER

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'


def mutations(generated, output):
    rejected = {}
    for name in ('original-equation', 'source-clock', 'observation-lane', 'ancestor-route',
                 'missing-row', 'aliased-state-id', 'wrong-offset', 'cut-certificate',
                 'restore-enabled', 'added-owner', 'image-admission', 'staging-source',
                 'driver-hash', 'declaration-hash', 'staging-abi'):
        case = output / name
        shutil.copytree(generated, case)
        binding = json.loads((case / 'binding.json').read_text())
        actual = (case / 'instrumented.fir').read_text()
        source = (case / 'host.fir').read_text()
        rows = binding['state']
        modules = parse_modules(source)
        root = re.search(r'^circuit (\w+) :', source, re.M)[1]
        if name == 'original-equation':
            module = rows[0]['module']
            register = rows[0]['hierarchy'].rsplit('.', 1)[1]
            text = re.search(r'^  module ' + module + r' :[\s\S]*?(?=^  (?:module|extmodule) |\Z)', actual, re.M)[0]
            old = re.search(r'^    ' + register + r' <= [^\n]+', text, re.M)[0]
            actual = actual.replace(old, f'    {register} <= UInt<{rows[0]["width"]}>("h0")', 1)
        elif name == 'source-clock':
            source = source.replace(', clock with :', ', asClock(reset) with :', 1)
            actual = actual.replace(', clock with :', ', asClock(reset) with :', 1)
        elif name in ('observation-lane', 'ancestor-route'):
            choices = list(re.finditer(r'^    ' + OBS + r' <= ([^\n]+)', actual, re.M))
            choice = choices[0] if name == 'observation-lane' else choices[-1]
            actual = actual[:choice.start(1)] + 'UInt<1>("h0")' + actual[choice.end(1):]
        elif name == 'missing-row':
            binding['state'] = rows[:-1]
        elif name == 'aliased-state-id':
            rows[1]['state_id'] = rows[0]['state_id']
        elif name == 'wrong-offset':
            rows[1]['offset'] += 1
        elif name == 'cut-certificate':
            actual = actual.replace(f'{ADAPTER}.functional_frozen <= {PREFIX}functional_frozen',
                                    f'{ADAPTER}.functional_frozen <= UInt<1>("h1")')
        elif name == 'restore-enabled':
            actual = actual.replace('parameter RESTORE_ENABLE = 0', 'parameter RESTORE_ENABLE = 1')
        elif name == 'added-owner':
            marker = f'    {OBS} <= '
            index = actual.index(marker)
            actual = actual[:index] + '    reg hidden_owner : UInt<1>, clock\n    hidden_owner <= reset\n' + actual[index:]
        elif name == 'image-admission':
            binding['complete_fpga_capture'] = True
        elif name in ('driver-hash', 'declaration-hash'):
            rows[0]['driver_sha256' if name == 'driver-hash' else 'declaration_sha256'] = '0'*64
        elif name == 'staging-abi':
            actual = actual.replace('output snapshot_state : UInt<', 'output snapshot_state : SInt<')
        else:
            p = case / 'generated.register-snapshot.sv'
            p.write_text(p.read_text().replace('payload <= live_state;', "payload <= live_state ^ 1'b1;"))
            binding['staging_source_sha256'] = file_sha(p)
        (case / 'host.fir').write_text(source)
        (case / 'instrumented.fir').write_text(actual)
        binding['source_sha256'] = sha(source)
        binding['instrumented_sha256'] = sha(actual)
        (case / 'binding.json').write_text(json.dumps(binding))
        try:
            audit(case)
        except FormatError as error:
            rejected[name] = str(error)
        else:
            raise FormatError('accepted register snapshot corruption ' + name)
    return rejected


def negative_wave(path):
    """Read first-word/cut/ack labels independently from the flushed raw VCD."""
    names = {PREFIX+'cut_cycle', PREFIX+'word_address', 'acknowledged_words', 'host_step'}
    scopes, codes, values, times = [], {}, {}, []
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == '$scope':
            scopes.append(parts[2])
        elif parts[0] == '$upscope':
            scopes.pop()
        elif parts[0] == '$var' and scopes == ['register_snapshot_tb'] and parts[4] in names:
            codes[parts[4]] = parts[3]
        elif line.startswith('#'):
            times.append(int(line[1:]))
        elif line.startswith('b') and len(parts) == 2:
            values[parts[1]] = parts[0][1:]
        elif line[0] in '01xz':
            values[line[1:]] = line[0]
    require(set(codes) == names and len(times) > 10 and times[-1] > 0 and
            all(re.fullmatch('[01]+', values.get(c, 'x')) for c in codes.values()),
            'incomplete/unflushed negative debug waveform')
    labels = {n: int(values[c], 2) for n, c in codes.items()}
    require(labels[PREFIX+'cut_cycle'] == 100 and labels[PREFIX+'word_address'] == 0 and
            labels['acknowledged_words'] == 0 and labels['host_step'] > 128,
            'negative waveform did not retain first-word/cut/ack labels')
    return labels


def bench(directory):
    original = parse_modules((directory / 'host.fir').read_text())
    actual = parse_modules((directory / 'instrumented.fir').read_text())
    root = re.search(r'^circuit (\w+) :', (directory / 'host.fir').read_text(), re.M)[1]
    binding = json.loads((directory / 'binding.json').read_text())
    bits, words = binding['bits'], binding['words']
    lines = ['`timescale 1ns/1ps', 'module register_snapshot_tb;',
             'import "DPI-C" function void checkpoint_widget_failed();']
    for name, (direction, kind) in actual[root]['ports'].items():
        width = 1 if kind == 'Clock' else int(re.fullmatch(r'UInt<(\d+)>', kind)[1])
        shape = '' if width == 1 else f'[{width-1}:0] '
        lines.append(f'{"reg" if direction == "input" else "wire"} {shape}{name}' +
                     (f'={width}\'d{int(name in ("reset", PREFIX+"reset"))};' if direction == 'input' else ';'))
        if direction == 'output' and name in original[root]['ports']:
            lines.append(f'wire {shape}ref_{name};')
    lines += [f'{root} dut(.*);', 'Reference' + root + ' original(' + ','.join(
        f'.{name}({"ref_" if direction == "output" else ""}{name})'
        for name, (direction, _) in original[root]['ports'].items()) + ');',
        f'reg [{bits-1}:0] expected;', 'integer checks=0,host_step=0,cuts=0,acknowledged_words=0;',
        'integer enqueue_fires=0,dequeue_fires=0,blocked_enqueues=0,staged_enqueue_fires=0,staged_dequeue_fires=0;',
        'function automatic [11:0] queue_tag(input integer address);',
        'queue_tag=12\'(((address%64)*13%64)*64+(address%64));endfunction',
        'task check(input bit okay,input string signal);checks++;if(!okay)begin',
        f'$display("REGISTER_SNAPSHOT_DIVERGENCE source_cut=%0d host_step=%0d acknowledged_words=%0d signal=%s",{PREFIX}cut_cycle,host_step,acknowledged_words,signal);',
        '$dumpflush;#0.001;checkpoint_widget_failed();$finish;end endtask',
        'task compare;']
    for name, (direction, _) in original[root]['ports'].items():
        if direction == 'output':
            lines.append(f'check({name}===ref_{name},"original_{name}");')
    vector = []
    for row in reversed(binding['state']):
        hierarchy = 'original.' + row['hierarchy'].split('.', 1)[1]
        vector.append(hierarchy)
    expression = '{' + ','.join(vector) + '}'
    lines += [f'check({OBS}==={expression},"complete_live_vector");endtask',
              'task tick;clock=0;#3;']
    if root != 'Top':
        lines += ['if(!reset)begin',
                  'if(io_enq_valid&&io_enq_ready)begin enqueue_fires++;',
                  f'if({PREFIX}valid)staged_enqueue_fires++;end',
                  'if(io_enq_valid&&!io_enq_ready)blocked_enqueues++;']
        for i in range(16):
            lines += [f'if(io_deq_{i}_valid&&io_deq_{i}_matches)begin dequeue_fires++;',
                      f'if({PREFIX}valid)staged_dequeue_fires++;end']
        lines += ['end']
    lines += ['clock=1;#3;compare();clock=0;#3;host_step++;endtask', 'task activity;']
    if root == 'Top':
        lines += ["enable=(host_step%3!=1);data={1'b1,32'(host_step*13),32'(host_step*7+5)};"]
    else:
        lines += ['io_enq_valid=(host_step%7!=3);io_enq_bits_tag=queue_tag(host_step);io_enq_bits_data=(host_step/64+host_step*7+13)%16;']
        for name in original[root]['ports']:
            match = re.fullmatch(r'io_deq_(\d+)_(valid|tag)', name)
            if match:
                i = int(match[1])
                value = f'(host_step>140&&host_step%5=={i%5})' if match[2] == 'valid' else f'queue_tag(host_step+{i}*3)'
                lines.append(f'{name}={value};')
    lines += ['endtask', 'task cut(input [63:0] label);',
              f'{PREFIX}target_cycle=label;{PREFIX}request=1;#1;',
              f'check({PREFIX}request_ready,"capture_ready");expected={expression};',
              # Initial queue data/tag contents are unknown in ordinary VCS;
              # warm all slots through real enqueue, never simulator writes.
              'check(!$isunknown(expected),"all_original_state_initialized");tick();',
              f'{PREFIX}request=0;#1;check({PREFIX}valid&&{PREFIX}cut_cycle==label,"captured_cut");',
              f'for(integer word=0;word<{words};word++)begin',
              f'{PREFIX}word_address=word;#1;',
              'repeat(3)begin',
              f'check({PREFIX}valid&&!{PREFIX}word_error&&{PREFIX}word_data===64\'(expected>>(word*64)),"immutable_word_before_ack");',
              'activity();tick();end acknowledged_words++;end',
              f'{PREFIX}word_address={words};#1;check({PREFIX}word_error&&{PREFIX}word_data==0,"invalid_word");',
              f'{PREFIX}word_address=32\'hffffffff;#1;check({PREFIX}word_error&&{PREFIX}word_data==0,"overflow_word");',
              f'{PREFIX}release_snapshot=1;#1;check(!{PREFIX}valid,"release_before_edge");tick();',
              f'{PREFIX}release_snapshot=0;#1;check(!{PREFIX}valid&&!{PREFIX}failed,"release_complete");cuts++;endtask',
              'initial begin $dumpfile("register-snapshot.vcd");$dumpvars(0,register_snapshot_tb);',
              'tick();tick();reset=0;', f'{PREFIX}reset=0;{PREFIX}owners_present=1;{PREFIX}functional_frozen=1;',
              # First initialize every exact queue slot with enqueue enabled.
              'for(integer i=0;i<128;i++)begin activity();']
    if root != 'Top':
        lines += ['io_enq_valid=1;io_enq_bits_tag=queue_tag(i);io_enq_bits_data=i%16;']
    lines += ['tick();end', 'for(integer i=0;i<512;i++)begin activity();tick();',
              'if(i==4||i==120||i==300||i==499)cut(100+cuts);end',
              f'check(cuts==4&&acknowledged_words=={words*4},"complete_scope");']
    if root != 'Top':
        lines += ['check(enqueue_fires>64&&dequeue_fires>0&&blocked_enqueues>0&&staged_enqueue_fires>0&&staged_dequeue_fires>0,"active_backpressured_queue_during_staging");',
                  '$display("REGISTER_SNAPSHOT_QUEUE_TRAFFIC enqueues=%0d dequeues=%0d blocked=%0d staged_enqueues=%0d staged_dequeues=%0d",enqueue_fires,dequeue_fires,blocked_enqueues,staged_enqueue_fires,staged_dequeue_fires);']
    lines += [
              f'{PREFIX}owners_present=0;{PREFIX}request=1;#1;check(!{PREFIX}request_ready&&!{PREFIX}valid&&{PREFIX}failed,"missing_owner_before_edge");tick();',
              f'{PREFIX}owners_present=1;{PREFIX}request=0;check({PREFIX}failed,"sticky_owner_fault");',
              f'{PREFIX}reset=1;tick();{PREFIX}reset=0;check(!{PREFIX}failed,"reset_recovery");',
              f'{PREFIX}request=1;tick();{PREFIX}request=0;{PREFIX}target_cycle++;#1;',
              f'check(!{PREFIX}valid&&{PREFIX}failed,"cycle_drift_before_edge");tick();',
              f'{PREFIX}reset=1;tick();{PREFIX}reset=0;',
              f'{PREFIX}functional_frozen=0;{PREFIX}request=1;#1;check(!{PREFIX}request_ready&&{PREFIX}failed,"missing_freeze");tick();',
              '$display("REGISTER_SNAPSHOT_PASS cuts=%0d words=%0d checks=%0d host_steps=%0d",cuts,acknowledged_words,checks,host_step);$finish;end endmodule']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('vivado', 'vcs'))
    parser.add_argument('--generated', required=True, type=Path)
    parser.add_argument('--compiler-receipt', required=True, type=Path)
    parser.add_argument('--reference-binding', required=True, type=Path)
    parser.add_argument('--reference-receipt', required=True, type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    generated, compiler, base = (local(ROOT, p).resolve() for p in (args.generated, args.compiler_receipt, args.out))
    require(all(p.is_relative_to(RUNS) for p in (generated, compiler, base)), 'all evidence belongs beneath runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=base))
    source_paths = [Path(__file__), Path(__file__).with_name('audit_register_snapshot.py'),
                    Path(__file__).with_name('audit_physical_clock_plan.py'),
                    Path(__file__).with_name('checkpoint_widget_exit.cc')]
    source_paths += list((ROOT/'sims/firesim/sim/midas/src/main/scala/midas/checkpoint').glob('*.scala'))
    source_paths += [ROOT/'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointRegisterSnapshotSpec.scala',
                     ROOT/'tools/checkpoint_formats/tests/RegisterSnapshotReference.scala',
                     ROOT/'sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv']
    sources = {str(p.relative_to(ROOT)): file_sha(p) for p in source_paths}
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               scope='live register subtree compiler/staging component only', physical_fpga_capture=False,
               deployable_capture_image=False, observed_utc=datetime.now(timezone.utc).isoformat(),
               generated_path=str(generated), sources=sources, commands=[])

    def run(argv, name, cwd=out, expected=0):
        log = out/(name+'.log')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as f:
            row['returncode'] = subprocess.run(row['argv'], cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log '+str(log))
        return log.read_text()

    try:
        c = json.loads(compiler.read_text())
        require(c['status'] == 'pass' and c['returncode'] == 0 and c['backend'] == 'f2', 'passing compiler receipt required')
        for name, h in c['sources'].items():
            require(file_sha(local(ROOT, name)) == h, 'compiler source changed '+name)
        names = [p.name for p in generated.iterdir() if p.is_file()]
        doc['generated'] = {n: file_sha(generated/n) for n in names}
        require(all(c['artifacts'].get(str((generated/n).relative_to(compiler.parent))) == file_sha(generated/n)
                    for n in names), 'generated files are not bound to compiler')
        doc['compiler_receipt'] = dict(path=str(compiler), sha256=file_sha(compiler))
        reference_binding, reference_receipt = (local(ROOT, p).resolve() for p in
                                               (args.reference_binding, args.reference_receipt))
        require(all(p.is_relative_to(RUNS) for p in (reference_binding, reference_receipt)), 'reference evidence escaped runs')
        oracle = bind_reference_receipt(reference_binding, reference_receipt)
        require(oracle['status'] == 'pass' and oracle['returncode'] == 0 and
                oracle['compiler_receipt']['sha256'] == file_sha(compiler), 'unbound oracle emission')
        for name, h in oracle['sources'].items():
            require(file_sha(local(ROOT, name)) == h, 'oracle emission source changed '+name)
        for name, h in oracle['artifacts'].items():
            require(file_sha(reference_receipt.parent/name) == h, 'oracle artifact changed '+name)
        doc['reference_receipt'] = dict(path=str(reference_receipt), sha256=file_sha(reference_receipt))
        doc['reference_binding'] = dict(path=str(reference_binding), sha256=file_sha(reference_binding))
        doc['reference_audit'] = audit_reference(reference_binding.parent, generated)
        shutil.copytree(generated, out/'generated')
        doc['audit'] = audit(out/'generated')
        doc['rejected_mutations'] = mutations(out/'generated', out)
        for n in ('instrumented.sv', 'generated.register-snapshot.sv'):
            shutil.copyfile(generated/n, out/n)
        binding = json.loads((generated/'binding.json').read_text())
        root = re.search(r'^circuit (\w+) :', (generated/'host.fir').read_text(), re.M)[1]
        bits = binding['bits']
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'native synthesis belongs on manager')
            (out/'synth.tcl').write_text(f'''set_param general.maxThreads 4
read_verilog -sv instrumented.sv
read_verilog -sv generated.register-snapshot.sv
synth_design -top {root} -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set payload [get_cells -hier -filter {{NAME =~ *checkpoint_register_snapshot_adapter/payload_reg* && IS_SEQUENTIAL == 1}}]
if {{[llength $payload] != {bits}}} {{error "incomplete native staged payload"}}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
write_verilog -force synthesized.v
write_checkpoint -force synthesized.dcp
puts "REGISTER_SNAPSHOT_SYNTH_PASS payload_bits={bits}"
''')
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'native')
            require(f'REGISTER_SNAPSHOT_SYNTH_PASS payload_bits={bits}' in text and 'ERROR:' not in text,
                    'native staging qualification incomplete')
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and
                    toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 required')
            native = local(ROOT, args.native).resolve()
            n = json.loads((native/'summary.json').read_text())
            require(n['status'] == 'pass' and n['sources'] == sources and n['generated'] == doc['generated'],
                    'stale native provenance')
            require(n['reference_binding']['sha256'] == file_sha(reference_binding) and
                    n['reference_receipt']['sha256'] == file_sha(reference_receipt), 'native oracle provenance changed')
            for name, h in n['artifacts'].items():
                require(file_sha(native/name) == h, 'native artifact changed '+name)
            doc['native_receipt'] = dict(path=str(native/'summary.json'), sha256=file_sha(native/'summary.json'))
            reference = (reference_binding.parent/'reference.sv').read_text()
            for name in parse_modules((generated/'host.fir').read_text()):
                reference = re.sub(r'\b'+re.escape(name)+r'\b', 'Reference'+name, reference)
            (out/'reference.sv').write_text(reference)
            (out/'bench.sv').write_text(bench(generated))
            rtl = (generated/'generated.register-snapshot.sv').read_text()
            require(rtl.count('payload <= live_state;') == 1, 'ambiguous corruption target')
            (out/'corrupt.sv').write_text(rtl.replace('payload <= live_state;', "payload <= live_state ^ 1'b1;"))
            for case in ('healthy', 'corrupt'):
                binary = out/('simv-'+case)
                run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                     '-top', 'register_snapshot_tb', '-Mdir='+str(out/('csrc-'+case)), '-o', binary,
                     out/'instrumented.sv', out/('generated.register-snapshot.sv' if case == 'healthy' else 'corrupt.sv'),
                     out/'reference.sv', out/'bench.sv', ROOT/'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
                     '-CFLAGS', '-std=c++17'], case+'-compile')
                work = out/case
                work.mkdir()
                text = run([binary, '-no_save'], case, work, 0 if case == 'healthy' else 1)
                expected = f'REGISTER_SNAPSHOT_PASS cuts=4 words={binding["words"]*4}'
                require(expected in text if case == 'healthy' else
                        'REGISTER_SNAPSHOT_DIVERGENCE source_cut=100' in text and
                        'acknowledged_words=0 signal=immutable_word_before_ack' in text,
                        'incomplete run or corruption escaped first-word check')
                if case == 'healthy' and root != 'Top':
                    traffic = re.search(r'REGISTER_SNAPSHOT_QUEUE_TRAFFIC enqueues=(\d+) dequeues=(\d+) '
                                        r'blocked=(\d+) staged_enqueues=(\d+) staged_dequeues=(\d+)', text)
                    require(traffic is not None and all(int(v) > 0 for v in traffic.groups()) and
                            int(traffic[1]) > 64, 'missing actual queue activity during staged readout')
                    doc['queue_traffic'] = dict(zip(('enqueues', 'dequeues', 'blocked',
                                                    'staged_enqueues', 'staged_dequeues'),
                                                   map(int, traffic.groups())))
                wave = work/'register-snapshot.vcd'
                require(wave.stat().st_size > 1000 and len(re.findall(r'^#\d+', wave.read_text(), re.M)) > 10,
                        'missing runtime debug waveform')
                if case == 'corrupt':
                    doc['negative_wave_labels'] = negative_wave(wave)
        require(all(file_sha(ROOT/n) == h for n, h in sources.items()), 'verification sources changed')
        doc['status'] = 'pass'
    except Exception as error:
        doc['error'] = str(error)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): file_sha(p) for p in out.rglob('*') if p.is_file() and
                            p.suffix in {'.sv', '.v', '.fir', '.json', '.log', '.rpt', '.tcl', '.dcp', '.vcd'}}
        receipt = out/'summary.json'
        receipt.write_text(json.dumps(doc, indent=2)+'\n')
        print(receipt, flush=True)


if __name__ == '__main__':
    main()
