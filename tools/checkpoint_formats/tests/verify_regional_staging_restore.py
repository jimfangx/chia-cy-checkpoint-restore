"""Qualify generated regional staging-owner restore on localhost and EDA SP2.

Original controller/endpoints are prepared independently through public inputs;
only the staging owner migrates. This cannot establish FPGA or CPU acceptance.
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
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_region_cut_snapshot_attachment import audit, audit_negatives
from tools.checkpoint_formats.tests.audit_native_snapshot_restore_wave import audit as wave
from tools.checkpoint_formats.tests.audit_regional_staging_restore import audit as epoch
from tools.checkpoint_formats.tests.verify_region_cut_snapshot import compiler_fixture

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
TB = 'tools/checkpoint_formats/tests/regional_staging_restore_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = (TB, EXIT, 'tools/checkpoint_formats/tests/verify_regional_staging_restore.py',
    'tools/checkpoint_formats/tests/audit_region_cut_snapshot_attachment.py',
    'tools/checkpoint_formats/tests/audit_native_snapshot_restore_wave.py',
    'tools/checkpoint_formats/tests/audit_regional_staging_restore.py',
    'tools/checkpoint_formats/tests/verify_region_cut_snapshot.py',
    'tools/checkpoint_formats/tests/native_regions_fixture.sv',
    'tools/checkpoint_formats/toolchain.py', 'tools/checkpoint_formats/codec.py',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointRegionCutSnapshot.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointRegionCutSnapshot.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointRegionCutSnapshotSpec.scala')
CUTS = ('empty', 'occupied', 'released', 'error')
NEGATIVES = ('missing-owner', 'physical-fault', 'request', 'release', 'borrow', 'unheld', 'busy', 'reset', 'label-drift')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture(bits):
    """Retain every original execution; connect the emitted public restore ABI."""
    original = (ROOT / 'tools/checkpoint_formats/tests/native_regions_fixture.sv').read_text()
    original = original.replace('input wire clock, reset,',
        'input wire [63:0] cut_cycle_xor,\n  input wire clock, reset,')
    first = original.index('  CheckpointPhysicalClockCut #')
    last = original.index('  NativeHost host(.*);', first)
    original = original[:first] + '''  wire [63:0] cut_input_cycle = cycle ^ cut_cycle_xor;
  NativeHost host(
    .capture_cut_freeze_request(freeze_request),
    .capture_cut_owner_present(owner_present), .capture_cut_target_cycle(cut_input_cycle),
    .capture_cut_stopped(), .capture_cut_failed(failed), .capture_cut_cycle(cut_cycle),
    .capture_cut_error(error), .capture_cut_control_state(), .capture_cut_pending(), .*);
''' + original[last+len('  NativeHost host(.*);\n'):]
    text = compiler_fixture(original).replace('[74:0]', f'[{bits-1}:0]').replace('[145:0]', f'[{bits+70}:0]')
    pins = '''    .capture_snapshot_restore_hold(restore_hold), .capture_snapshot_restore_load(restore_load),
    .capture_snapshot_restore_state(restore_state), .capture_snapshot_restore_ready(restore_ready),
'''
    text = text.replace('  NativeHost host(\n', '  NativeHost host(\n' + pins)
    ports = f'''  input wire restore_hold, restore_load,
  input wire [{bits+70}:0] restore_state, output wire restore_ready,
'''
    if bits == 82:
        ports += '  output wire [6:0] capture_router_state,\n'
    return text.replace('module NativeRegionsFixture(\n', 'module NativeRegionsFixture(\n' + ports)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    ap.add_argument('--compiler', type=Path)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    require(a.out.resolve().is_relative_to(RUNS), 'evidence beneath runs required')
    a.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=a.mode+'-', dir=a.out.resolve()))
    sources = {name: sha(ROOT/name) for name in SOURCES}
    doc = dict(status='running', backend='f2' if a.mode == 'vivado' else 'eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), source_root=str(ROOT),
        sources=sources, commands=[], cases=[],
        scope='generated regional complete staging owner only; independently prepared original endpoints/controller',
        physical_fpga_capture=False, full_image=False, CPU_migration_verified=False)
    summary = out/'summary.json'

    def save():
        summary.write_text(json.dumps(doc, indent=2)+'\n')

    def run(argv, name, cwd=out, expected=0):
        log = out/(name+'.log')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log))
        doc['commands'].append(row)
        save()
        with log.open('x') as stream:
            r = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row.update(returncode=r.returncode, log_sha256=sha(log))
        save()
        require(r.returncode == expected, 'inspect underlying compiler/runtime log '+str(log))
        return log.read_text()

    save()
    print(out, flush=True)
    try:
        if a.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and a.compiler and not a.native,
                    'current manager compiler receipt required')
            cp = local(ROOT, a.compiler)
            compiler = json.loads(cp.read_text())
            require(compiler['status'] == 'pass' and compiler['backend'] == 'f2', 'successful compiler required')
            for n, h in compiler['sources'].items():
                require(sha(local(ROOT, n)) == h, 'changed compiler source '+n)
            doc['compiler'] = dict(path=str(cp), sha256=sha(cp))
            doc['sources'].update(compiler['sources'])
            vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
            for name, src in [('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')]:
                shutil.copyfile(src, out/name)
            for bits in (75, 82):
                work = out/f'bits-{bits}'
                work.mkdir()
                name = 'native-regions-cut-' + ('router-' if bits == 82 else '') + 'staging-restore'
                source = cp.parent/'generated/bank'/name
                for f in source.rglob('*'):
                    if f.is_file():
                        require(compiler['artifacts'].get(str(f.relative_to(cp.parent))) == sha(f), 'unbound compiler artifact')
                shutil.copytree(source, work/'generated')
                row = dict(bits=bits, attachment=audit(work/'generated'),
                    negative_audits=audit_negatives(work/'generated', work/'negative-audits'))
                (work/'fixture.sv').write_text(fixture(bits))
                files = ['generated/staged.sv'] + [str(f.relative_to(work)) for f in
                    sorted((work/'generated').glob('FireSim-generated*.sv'))] + ['fixture.sv']
                (work/'files.json').write_text(json.dumps(files, indent=2)+'\n')
                (work/'fixture.synthesis.xdc').write_bytes((work/'generated/instrumented.synthesis.xdc').read_bytes())
                (work/'fixture.implementation.xdc').write_text((work/'generated/instrumented.implementation.xdc')
                    .read_text().replace('shell/CL/', 'host/'))
                tcl = 'set_param general.maxThreads 4\nread_verilog -sv ' + ' '.join(files) + f'''
read_xdc fixture.synthesis.xdc
synth_design -top NativeRegionsFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
source fixture.implementation.xdc
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set regs [get_cells -hier -filter {{NAME =~ host/checkpoint_region_cut_snapshot/staging/* && IS_SEQUENTIAL == 1}}]
if {{[llength $regs] != {bits+71}}} {{error "incomplete original staging owner: [llength $regs]"}}
set raw [get_nets -of_objects [get_ports clock]]
foreach cell $regs {{
  set pins [get_pins -of_objects $cell -filter {{REF_PIN_NAME == C}}]
  if {{[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0}} {{error "staging left raw clock"}}
}}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force staging.dcp
puts "REGIONAL_STAGING_SYNTH_PASS bits={bits+71}"
'''
                (work/'synth.tcl').write_text(tcl)
                text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], f'bits-{bits}-synthesis', cwd=work)
                require('REGIONAL_STAGING_SYNTH_PASS' in text and not re.search('ERROR:|CRITICAL WARNING:', text),
                        'native synthesis failed')
                doc['cases'].append(row)
                save()
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and a.native and not a.compiler and
                toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA native SP2 and synthesized fixture required')
            np = local(ROOT, a.native)
            native = json.loads(np.read_text())
            require(native['status'] == 'pass' and native['backend'] == 'f2', 'successful localhost synthesis required')
            for n, h in native['sources'].items():
                require(sha(ROOT/n) == h, 'native source changed '+n)
            for n, h in native['artifacts'].items():
                require(sha(np.parent/n) == h, 'native artifact changed '+n)
            doc['native'] = dict(path=str(np), sha256=sha(np))
            for bits in (75, 82):
                work = out/f'bits-{bits}'
                work.mkdir()
                original = np.parent/f'bits-{bits}'
                for name in ('generated', 'fixture.sv', 'files.json'):
                    src = original/name
                    if src.is_dir():
                        shutil.copytree(src, work/name)
                    else:
                        shutil.copyfile(src, work/name)
                files = [work/f for f in json.loads((work/'files.json').read_text())]
                flags = [toolchain.VCS, '-full64', '-sverilog', '-Mupdate', '-debug_access+all', '-timescale=1ns/1ps',
                    '-cc', toolchain.CC, '-cpp', toolchain.CXX, f'+define+CONTROL_BITS={bits}',
                    *(['+define+WITH_ROUTERS'] if bits == 82 else []),
                    '-top', 'regional_staging_restore_tb', '-top', 'glbl']
                binary = work/'simv'
                tail = [np.parent/'BUFGCE.v', np.parent/'glbl.v', ROOT/TB, ROOT/EXIT]
                run([*flags, '-Mdir='+str(work/'csrc'), '-o', binary, *files, *tail], f'bits-{bits}-compile', cwd=work)
                row = dict(bits=bits, attachment=audit(work/'generated'), modes=[])
                for cut in CUTS:
                    image = work/(cut+'.state')
                    for mode in ('donor', 'restore'):
                        scenarios = ['healthy']
                        if mode == 'restore' and cut == 'occupied':
                            scenarios += ['bits', *NEGATIVES]
                        for scenario in scenarios:
                            name = f'{cut}-{mode}-{scenario}'
                            dest = work/name
                            dest.mkdir()
                            text = run([binary, '-no_save', '+MODE='+mode, '+CUT='+cut, '+CASE='+scenario,
                                '+IMAGE='+str(image)], f'bits-{bits}-{name}', cwd=dest)
                            require('REGIONAL_STAGING_' + ('DONOR_PASS' if mode == 'donor' else
                                'RESTORE_PASS' if scenario in ('healthy', 'bits') else 'NEGATIVE_PASS') in text,
                                'missing healthy completion or expected rejection')
                            result = dict(cut=cut, mode=mode, scenario=scenario, image_sha256=sha(image))
                            if mode == 'restore':
                                loads = 2*(bits+71)+2 if scenario == 'bits' else 2 if scenario == 'label-drift' else 1
                                result['wave'] = wave(dest/'regional-staging-restore.vcd', bits, loads=loads,
                                    top='regional_staging_restore_tb.', owner='dut.host.checkpoint_region_cut_snapshot.staging.',
                                    reset_signal='capture_reset')
                                if scenario == 'healthy':
                                    donor = int(image.read_text().strip(), 16)
                                    result['epoch'] = epoch(dest/'regional-staging-restore.vcd', bits, donor)
                                    if cut == 'occupied':
                                        rejected = []
                                        for bit in range(bits+71):
                                            try:
                                                epoch(dest/'regional-staging-restore.vcd', bits, donor, mutate_bit=bit)
                                            except ValueError:
                                                rejected.append(bit)
                                            else:
                                                raise ValueError('wave checker admitted changed staging bit '+str(bit))
                                        result['checker_mutations_rejected'] = rejected
                            row['modes'].append(result)
                            save()
                # Compile a semantic fault into a separate copied staging
                # implementation, retaining every exact original native input.
                bad = work/'corrupt-generated'
                shutil.copytree(work/'generated', bad)
                resource = bad/'FireSim-generated.native-region-cut-staging.sv'
                text = resource.read_text()
                old = 'payload <= restore_state[BITS-1:0];'
                require(text.count(old) == 1, 'ambiguous deliberate semantic mutation')
                resource.write_text(text.replace(old, old.replace(';', " ^ {{(BITS-1){1'b0}},1'b1};")))
                corrupt_files = [str(work/f.replace('generated/', 'corrupt-generated/')) for f in json.loads((work/'files.json').read_text())]
                broken = work/'corrupt-simv'
                run([*flags, '-Mdir='+str(work/'corrupt-csrc'), '-o', broken, *corrupt_files, *tail],
                    f'bits-{bits}-corrupt-compile', cwd=work)
                dest = work/'corrupt'
                dest.mkdir()
                image = work/'occupied.state'
                text = run([broken, '-no_save', '+MODE=restore', '+CUT=occupied', '+CASE=healthy', '+IMAGE='+str(image)],
                    f'bits-{bits}-corrupt-first-load', cwd=dest, expected=1)
                require('REGIONAL_STAGING_FIRST_DIVERGENCE signal=complete-owner-before-ack cut=38' in text and
                    'loads=1 acknowledged_requests=0 acknowledged_responses=0' in text, 'missing first unacknowledged semantic divergence')
                row['compiled_corruption'] = epoch(dest/'regional-staging-restore.vcd', bits,
                    int(image.read_text().strip(), 16), corrupt=True)
                doc['cases'].append(row)
                save()
        require(all(sha(ROOT/n) == h for n, h in doc['sources'].items()), 'qualification source changed')
        doc['status'] = 'pass'
    except BaseException as e:
        doc.update(status='fail', error=str(e))
        raise
    finally:
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        doc['artifacts'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*')
            if f.is_file() and not f.is_symlink() and f != summary}
        save()
        print(summary, flush=True)


if __name__ == '__main__':
    main()
