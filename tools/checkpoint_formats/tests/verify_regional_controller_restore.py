"""Qualify the generated parked cut-controller owner, never full CPU migration."""
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
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
TB = 'tools/checkpoint_formats/tests/regional_controller_restore_tb.sv'
SOURCES = (TB, 'tools/checkpoint_formats/tests/verify_regional_controller_restore.py',
    'tools/checkpoint_formats/tests/native_regions_fixture.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointRegionClockCut.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointRegionClockCutSpec.scala',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv',
    'tools/checkpoint_formats/toolchain.py', 'tools/checkpoint_formats/codec.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def attachment(directory):
    d = Path(directory)
    binding = json.loads((d/'cut-binding.json').read_text())
    text = (d/'attached.fir').read_text()
    modules = parse_modules(text)
    root, controller = modules['NativeHost'], modules['CheckpointPhysicalClockCut']
    require(binding['attached_sha256'] == sha(d/'attached.fir') and binding['cut_version'] == 2,
            'changed generated controller circuit/binding')
    require(binding['controller_definition_sha256'] == hashlib.sha256(controller['body'].encode()).hexdigest(),
            'changed complete controller declaration')
    require(binding['controller_source_sha256'] == sha(d/'FireSim-generated.native-region-cut-controller.sv'),
            'changed native controller resource')
    require(binding['control_state_bits'] == 75 and binding['controller_restore_supported'] is True and
            binding['controller_restore_extra_storage_bits'] == 0 and
            binding['controller_restore_unheld_load'] == 'reject_load_and_park_mask' and
            binding['controller_restore_contract'] ==
            'complete_vector_raw_posedge_and_negedge_under_permanent_hold_before_first_raw_edge',
            'changed whole-owner parked contract')
    for key in ('controller_restore_resume_supported', 'router_endpoint_functional_restore_supported',
                'complete_fpga_capture', 'deployable_capture_image', 'metasim_restore_supported'):
        require(binding[key] is False, 'unsupported image/continuation admission '+key)
    drivers = root['drivers']
    prefix = 'checkpoint_region_clock_cut.'
    expected = {
        'restore_hold': 'or(capture_cut_restore_hold, or(capture_cut_restore_load_pos, capture_cut_restore_load_neg))',
        'restore_load_pos': 'and(capture_cut_restore_hold, capture_cut_restore_load_pos)',
        'restore_load_neg': 'and(capture_cut_restore_hold, capture_cut_restore_load_neg)',
        'restore_state': 'bits(capture_cut_restore_state, 73, 0)', 'clock': binding['raw_clock'],
        'reset': 'capture_reset'}
    require(all(drivers.get(prefix+n) == v for n, v in expected.items()), 'incomplete controller restore route')
    pending = drivers['capture_cut_accepted_pending']
    require(pending.startswith('mux(capture_reset, UInt<1>("h0"), mux('+expected['restore_hold']) and
            'mux(and(capture_cut_restore_hold, capture_cut_restore_load_pos), bits(capture_cut_restore_state, 74, 74), capture_cut_accepted_pending)' in pending,
            'pending owner missing reset/load/hold priority')
    require(re.findall(r'parameter (\w+) = (\d+)', controller['body']) ==
            [('GATES', '4'), ('OWNERS', '1'), ('EXTERNAL_CLOCK_NETWORK', '1'), ('RESTORE_ENABLE', '1')],
            'changed physical owner geometry')
    return dict(status='pass', bits=75, positive_edge_bits=74, negative_edge_bits=1, complete_fpga_capture=False)


def attachment_negatives(directory, out):
    """Rehash each modified circuit so route audits, not checksums, reject it."""
    d, out = Path(directory), Path(out)
    text = (d/'attached.fir').read_text()
    mutations = {
        'unqualified-positive-load': ('and(capture_cut_restore_hold, capture_cut_restore_load_pos)', 'capture_cut_restore_load_pos'),
        'unqualified-negative-load': ('and(capture_cut_restore_hold, capture_cut_restore_load_neg)', 'capture_cut_restore_load_neg'),
        'missing-pending-owner': ('bits(capture_cut_restore_state, 74, 74)', 'UInt<1>("h0")'),
        'truncated-physical-owner': ('bits(capture_cut_restore_state, 73, 0)', 'bits(capture_cut_restore_state, 72, 0)'),
        'wrong-raw-clock': ('checkpoint_region_clock_cut.clock <= clock', 'checkpoint_region_clock_cut.clock <= stage.clock'),
        'disabled-restore-parameter': ('parameter RESTORE_ENABLE = 1', 'parameter RESTORE_ENABLE = 0'),
    }
    rejected = []
    for name, (before, after) in mutations.items():
        require(before in text, 'missing structural mutation site '+name)
        work = out/name
        work.mkdir(parents=True)
        changed = text.replace(before, after)
        (work/'attached.fir').write_text(changed)
        shutil.copyfile(d/'FireSim-generated.native-region-cut-controller.sv', work/'FireSim-generated.native-region-cut-controller.sv')
        binding = json.loads((d/'cut-binding.json').read_text())
        binding['attached_sha256'] = sha(work/'attached.fir')
        binding['controller_definition_sha256'] = hashlib.sha256(parse_modules(changed)['CheckpointPhysicalClockCut']['body'].encode()).hexdigest()
        (work/'cut-binding.json').write_text(json.dumps(binding, indent=2)+'\n')
        try:
            attachment(work)
        except ValueError as error:
            rejected.append(dict(name=name, reason=str(error), coherently_rehashed=True))
        else:
            raise ValueError('structural auditor admitted '+name)
    return rejected


def wave(path, *, mutate_bit=None, corrupt=False):
    top = 'regional_controller_restore_tb.'
    owner = top+'dut.host.checkpoint_region_clock_cut.'
    names = {n: top+n for n in ('clock', 'capture_reset', 'restore_hold', 'restore_load_pos',
        'restore_load_neg', 'restore_state', 'control_state', 'capture_clock_mask', 'capture_read_enable',
        'capture_request_ready', 'capture_response_valid', 'acknowledgements', 'functional_edges')}
    names.update({n: owner+n for n in ('freeze_low', 'sampled', 'release_pending', 'captured_ce', 'cut_cycle', 'error')})
    names['pending'] = top+'dut.host.capture_cut_accepted_pending'
    codes, scopes, values, previous = {}, [], {}, {}
    positive = negative = held = rejected = 0
    positive_initialized = negative_initialized = False

    def sample():
        nonlocal previous, positive, negative, held, rejected, positive_initialized, negative_initialized
        now = {n: int(values[c], 2) for n, c in codes.items() if re.fullmatch('[01]+', values.get(c, 'x'))}
        if now.get('clock') != previous.get('clock') and 'clock' in previous:
            p = previous
            require(p.get('capture_clock_mask') == 1 and p.get('capture_read_enable') == 0 and
                    p.get('capture_request_ready') == 0 and p.get('capture_response_valid') == 0,
                    'parked destination exposed a permission or handshake')
            require(now.get('acknowledgements') == now.get('functional_edges') == 0,
                    'destination advanced before owner readback')
            if now['clock'] == 1:
                if p.get('capture_reset'):
                    expected = 0
                    positive_initialized = True
                elif p.get('restore_hold') and p.get('restore_load_pos'):
                    expected = p['restore_state'] >> 1
                    positive += 1
                    positive_initialized = True
                elif positive_initialized:
                    expected = p['control_state'] >> 1
                    held += 1
                    rejected += int(p.get('restore_load_pos') == 1)
                else:
                    previous = now
                    return
                packed = now['sampled'] | now['release_pending'] << 1 | now['captured_ce'] << 2 | now['cut_cycle'] << 6 | now['error'] << 70 | now['pending'] << 73
                # Physical controller offsets are {error[2:0],cycle[63:0],
                # CE[3:0],release,sampled,freeze}; pending is the final bit.
                require(packed == expected, 'partial or altered original positive-edge owner')
            else:
                if p.get('capture_reset'):
                    expected = 0
                    negative_initialized = True
                elif p.get('restore_hold') and p.get('restore_load_neg'):
                    expected = p['restore_state'] & 1
                    negative += 1
                    negative_initialized = True
                elif negative_initialized:
                    expected = p['freeze_low']
                else:
                    previous = now
                    return
                require(now['freeze_low'] == expected, 'partial or altered original falling-edge owner')
            if positive_initialized and negative_initialized:
                packed = now['freeze_low'] | now['sampled'] << 1 | now['release_pending'] << 2 | now['captured_ce'] << 3 | now['cut_cycle'] << 7 | now['error'] << 71 | now['pending'] << 74
                if mutate_bit is not None:
                    packed ^= 1 << mutate_bit
                require(now['control_state'] == packed, 'readback omits original controller storage')
        previous = now

    for line in Path(path).read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == '$scope':
            scopes.append(parts[2])
        elif parts[0] == '$upscope':
            scopes.pop()
        elif parts[0] == '$var':
            full = '.'.join(scopes+[parts[4].lstrip('\\')])
            for role, name in names.items():
                if full == name:
                    codes[role] = parts[3]
        elif line.startswith('#'):
            sample()
        elif line[0] in 'bB' and len(parts) == 2:
            values[parts[1]] = parts[0][1:].lower()
        elif line[0] in '01xXzZ':
            values[line[1:].strip()] = line[0].lower()
    sample()
    require(codes.keys() == names.keys(), 'missing complete raw owner waveform '+str(names.keys()-codes.keys()))
    require(positive == negative == (1 if corrupt else 11), 'incomplete fresh controller load waveform')
    if not corrupt:
        require(held >= 88 and rejected == 11, 'missing hold/unheld-load coverage')
    return dict(positive_loads=positive, negative_loads=negative, held_edges=held,
                rejected_unheld_loads=rejected, acknowledged_edges=0, functional_edges=0)


def fixture():
    original = (ROOT/'tools/checkpoint_formats/tests/native_regions_fixture.sv').read_text()
    begin = original.index('  CheckpointPhysicalClockCut #')
    end = original.index('  NativeHost host(.*);', begin)
    replacement = '''  NativeHost host(
    .capture_cut_freeze_request(freeze_request), .capture_cut_target_cycle(controller_target_cycle),
    .capture_cut_owner_present(owner_present), .capture_cut_stopped(),
    .capture_cut_failed(failed), .capture_cut_cycle(cut_cycle), .capture_cut_error(error),
    .capture_cut_control_state(control_state), .capture_cut_pending(),
    .capture_cut_restore_hold(restore_hold), .capture_cut_restore_load_pos(restore_load_pos),
    .capture_cut_restore_load_neg(restore_load_neg), .capture_cut_restore_state(restore_state), .*);
'''
    original = original[:begin]+replacement+original[end+len('  NativeHost host(.*);\n'):]
    return original.replace('module NativeRegionsFixture(\n', '''module NativeRegionsFixture(
  input wire restore_hold, restore_load_pos, restore_load_neg,
  input wire [74:0] restore_state, output wire [74:0] control_state,
  input wire [63:0] controller_target_cycle,
''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('vivado', 'vcs'))
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'all evidence beneath runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    doc = dict(status='running', backend='f2' if args.mode == 'vivado' else 'eda',
        source_root=str(ROOT), host=socket.gethostname(), observed_utc=datetime.now(timezone.utc).isoformat(),
        sources={n: sha(ROOT/n) for n in SOURCES}, commands=[], physical_fpga_capture=False,
        full_image=False, CPU_migration_verified=False, scope='parked generated cut-controller and pending owner only')
    summary = out/'summary.json'

    def save():
        summary.write_text(json.dumps(doc, indent=2)+'\n')

    def run(argv, name, cwd=out, expected=0):
        log = out/(name+'.log')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log))
        doc['commands'].append(row)
        save()
        with log.open('x') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode, log_sha256=sha(log))
        save()
        require(result.returncode == expected, 'inspect compiler/runtime log '+str(log))
        return log.read_text()

    save()
    print(out, flush=True)
    try:
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and args.compiler and not args.native,
                    'current localhost compiler receipt required')
            cp = local(ROOT, args.compiler)
            compiler = json.loads(cp.read_text())
            require(compiler['status'] == 'pass' and compiler['backend'] == 'f2', 'successful compiler required')
            for n, h in compiler['sources'].items():
                require(sha(local(ROOT, n)) == h, 'compiler source changed '+n)
            doc.update(compiler=dict(path=str(cp), sha256=sha(cp)))
            doc['sources'].update(compiler['sources'])
            src = cp.parent/'generated/bank/native-regions-controller-restore'
            for p in src.rglob('*'):
                if p.is_file():
                    require(compiler['artifacts'].get(str(p.relative_to(cp.parent))) == sha(p), 'unbound compiler artifact')
            shutil.copytree(src, out/'generated')
            doc['attachment'] = attachment(out/'generated')
            doc['attachment_mutations_rejected'] = attachment_negatives(out/'generated', out/'negative-audits')
            vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
            for name in ('BUFGCE.v', 'glbl.v'):
                shutil.copyfile(vendor/('unisims' if name == 'BUFGCE.v' else '')/name, out/name)
            shutil.copyfile(ROOT/TB, out/'testbench.sv')
            shutil.copyfile(ROOT/'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc', out/'checkpoint_widget_exit.cc')
            (out/'fixture.sv').write_text(fixture())
            files = ['generated/attached.sv']+[str(p.relative_to(out)) for p in sorted((out/'generated').glob('FireSim-generated*.sv'))]+['fixture.sv']
            (out/'files.json').write_text(json.dumps(files, indent=2)+'\n')
            (out/'fixture.synthesis.xdc').write_bytes((out/'generated/instrumented.synthesis.xdc').read_bytes())
            (out/'fixture.implementation.xdc').write_text((out/'generated/instrumented.implementation.xdc').read_text().replace('shell/CL/', 'host/'))
            tcl = 'set_param general.maxThreads 4\nread_verilog -sv '+' '.join(files)+'''
read_xdc fixture.synthesis.xdc
synth_design -top NativeRegionsFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
source fixture.implementation.xdc
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set physical [get_cells -hier -filter {NAME =~ host/checkpoint_region_clock_cut/* && IS_SEQUENTIAL == 1}]
set pending [get_cells -hier -filter {NAME =~ host/capture_cut_accepted_pending* && IS_SEQUENTIAL == 1}]
if {[llength $physical] != 74 || [llength $pending] != 1} {error "incomplete physical/pending owner registers"}
set raw [get_nets -of_objects [get_ports clock]]
foreach cell [concat $physical $pending] {
  set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "controller owner left raw clock"}
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force controller.dcp
puts "REGIONAL_CONTROLLER_SYNTH_PASS physical_bits=74 pending_bits=1"
'''
            (out/'synth.tcl').write_text(tcl)
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synthesis')
            require('REGIONAL_CONTROLLER_SYNTH_PASS' in text and not re.search('ERROR:|CRITICAL WARNING:', text), 'native synthesis failed')
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and args.native and not args.compiler and
                    toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 and native receipt required')
            np = local(ROOT, args.native)
            native = json.loads(np.read_text())
            require(native['status'] == 'pass' and native['backend'] == 'f2', 'successful native synthesis required')
            for n, h in native['sources'].items():
                require(sha(ROOT/n) == h, 'native source changed '+n)
            for n, h in native['artifacts'].items():
                require(sha(np.parent/n) == h, 'native artifact changed '+n)
            doc['native'] = dict(path=str(np), sha256=sha(np))
            for name in ('generated', 'fixture.sv', 'files.json', 'BUFGCE.v', 'glbl.v', 'testbench.sv', 'checkpoint_widget_exit.cc'):
                src = np.parent/name
                if src.is_dir():
                    shutil.copytree(src, out/name)
                else:
                    shutil.copyfile(src, out/name)
            doc['attachment'] = attachment(out/'generated')
            manifest = json.loads((out/'generated/manifest.json').read_text())
            slot = next(r['slot'] for r in manifest['state'] if r['domain'] == 'functional' and r['region'] == 0 and r['hierarchy'].endswith('.cycles'))
            binary = out/'simv'
            files = [out/f for f in json.loads((out/'files.json').read_text())]
            run([toolchain.VCS, '-full64', '-sverilog', '-Mupdate', '-debug_access+all', '-timescale=1ns/1ps',
                 '-cc', toolchain.CC, '-cpp', toolchain.CXX, f'+define+CYCLE_SLOT={slot}',
                 '-top', 'regional_controller_restore_tb', '-top', 'glbl', '-Mdir='+str(out/'csrc'), '-o', binary,
                 *files, out/'BUFGCE.v', out/'glbl.v', out/'testbench.sv', out/'checkpoint_widget_exit.cc'], 'compile')
            doc['cases'] = []
            image = out/'source/controller.state'
            for mode in ('source', 'destination', 'corrupt-0', 'corrupt-74'):
                work = out/mode
                work.mkdir()
                corrupt = mode.startswith('corrupt-')
                argv = [binary, '-no_save', '+mode='+('destination' if corrupt else mode), '+image='+str(image)]
                if corrupt:
                    argv += ['+corrupt_bit='+mode.split('-')[1]]
                text = run(argv, mode, cwd=work, expected=1 if corrupt else 0)
                require(('REGIONAL_CONTROLLER_FIRST_DIVERGENCE' if corrupt else 'REGIONAL_CONTROLLER_RESTORE_PASS') in text,
                        'missing healthy completion/first divergence')
                row = dict(mode=mode)
                if mode != 'source':
                    row['wave'] = wave(work/'regional-controller-restore.vcd', corrupt=corrupt)
                if corrupt:
                    require('acknowledged_edges=0 functional_edges=0' in text, 'fault acknowledged an edge')
                doc['cases'].append(row)
                save()
            values = [tuple(int(x, 16) for x in line.split()) for line in image.read_text().splitlines()]
            require(len(values) == 11 and any(state >> 74 for state, _ in values) and
                    any((state >> 71) & 7 for state, _ in values), 'missing pending/fault actual donor coverage')
            doc['donor'] = dict(path=str(image), sha256=sha(image), values=values)
            rejected = []
            for bit in range(75):
                try:
                    wave(out/'destination/regional-controller-restore.vcd', mutate_bit=bit)
                except ValueError:
                    rejected.append(bit)
                else:
                    raise ValueError('wave checker admitted raw owner bit '+str(bit))
            doc['rejected_wave_checker_mutation_bits'] = rejected
        require(all(sha(ROOT/n) == h for n, h in doc['sources'].items()), 'qualification source changed')
        doc['status'] = 'pass'
    except BaseException as error:
        doc.update(status='fail', error=str(error))
        raise
    finally:
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        doc['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and not p.is_symlink() and p != summary}
        save()
        print(summary, flush=True)


if __name__ == '__main__':
    main()
