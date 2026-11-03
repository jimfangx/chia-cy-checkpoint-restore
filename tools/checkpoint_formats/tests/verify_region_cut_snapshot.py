"""Synthesize the atomic staging adapter on a compiler-generated regional cut.

Native Vivado belongs on this manager; VCS SP2 belongs exclusively on EDA.
The original source/compiler/native binding and all raw waves remain retained.
This bounded component cannot admit a deployable CPU checkpoint image.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require, FormatError
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha
from tools.checkpoint_formats.tests.audit_native_regions import audit as audit_regions
from tools.checkpoint_formats.tests.audit_native_region_cut import audit_cut
from tools.checkpoint_formats.tests.audit_region_cut_snapshot import audit as audit_wave

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointRegionCutSnapshot.sv'
STAGE = 'sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv'
TB = 'tools/checkpoint_formats/tests/native_region_cut_snapshot_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = (RTL, STAGE, TB, EXIT, 'tools/checkpoint_formats/tests/verify_region_cut_snapshot.py',
           'tools/checkpoint_formats/tests/audit_region_cut_snapshot.py')


def fixture(original):
    """Keep the original functional host and every original primitive in place."""
    original = original.replace('  input wire [63:0] cut_cycle_xor,', '''  input wire snapshot_request, snapshot_release,
  input wire [31:0] snapshot_word_address,
  output wire snapshot_ready, snapshot_valid, snapshot_failed, snapshot_word_error,
  output wire [63:0] snapshot_word_data, snapshot_cut_cycle,
  output wire [5:0] snapshot_error,
  output wire [74:0] captured_control_state,
  output wire [145:0] staging_control_state,
  output wire physical_read_enable,
  input wire [63:0] cut_cycle_xor,''')
    require(original.count('  NativeHost host(') == 1, 'changed exact regional fixture')
    original = original.replace('  NativeHost host(', '''  wire physical_failed, source_pending, cut_freeze_request;
  wire [74:0] live_control_state;
  wire source_request_valid, source_request_ready, source_response_valid, source_response_ready;
  wire [63:0] source_response_data;
  wire source_response_error;
  assign failed = physical_failed || snapshot_failed;
  assign capture_read_enable = snapshot_valid && physical_read_enable;
  CheckpointRegionCutSnapshot #(.CONTROL_BITS(75)) snapshot (
    .clock(clock), .reset(capture_reset), .host_freeze_request(freeze_request),
    .snapshot_request(snapshot_request), .snapshot_release(snapshot_release),
    .physical_read_enable(physical_read_enable), .physical_failed(physical_failed),
    .source_pending(source_pending), .target_cycle(cycle), .live_control_state(live_control_state),
    .cut_freeze_request(cut_freeze_request),
    .request_valid(capture_request_valid), .request_ready(capture_request_ready),
    .source_request_valid(source_request_valid), .source_request_ready(source_request_ready),
    .source_response_valid(source_response_valid), .source_response_ready(source_response_ready),
    .source_response_data(source_response_data), .source_response_error(source_response_error),
    .response_valid(capture_response_valid), .response_ready(capture_response_ready),
    .response_data(capture_response_data), .response_error(capture_response_error),
    .word_address(snapshot_word_address), .snapshot_ready(snapshot_ready), .snapshot_valid(snapshot_valid),
    .snapshot_failed(snapshot_failed), .word_data(snapshot_word_data), .cut_cycle(snapshot_cut_cycle),
    .word_error(snapshot_word_error), .snapshot_error(snapshot_error),
    .captured_control_state(captured_control_state), .staging_control_state(staging_control_state));
  NativeHost host(
    .capture_read_enable(physical_read_enable),
    .capture_request_valid(source_request_valid), .capture_request_ready(source_request_ready),
    .capture_response_valid(source_response_valid), .capture_response_ready(source_response_ready),
    .capture_response_data(source_response_data), .capture_response_error(source_response_error),''')
    for old, new in [('.capture_cut_freeze_request(freeze_request)', '.capture_cut_freeze_request(cut_freeze_request)'),
                     ('.capture_cut_failed(failed)', '.capture_cut_failed(physical_failed)'),
                     ('.capture_cut_control_state()', '.capture_cut_control_state(live_control_state)'),
                     ('.capture_cut_pending()', '.capture_cut_pending(source_pending)')]:
        require(original.count(old) == 1, 'changed exact fixture route ' + old)
        original = original.replace(old, new)
    return original


def check_parent(path):
    path = local(ROOT, path)
    doc = json.loads(path.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'f2' and doc['common_cut'] is True,
            'successful generated native common-cut receipt required')
    for n, h in doc['sources'].items():
        require(sha(local(ROOT, n)) == h, 'changed parent source ' + n)
    for group in ('inputs', 'artifacts'):
        for n, h in doc[group].items():
            require(sha(path.parent / n) == h, 'changed parent native evidence ' + n)
    cp = doc['compiler_receipt']
    compiler_path = local(ROOT, cp['path'])
    require(sha(compiler_path) == cp['sha256'], 'changed parent compiler receipt')
    compiler = json.loads(compiler_path.read_text())
    require(compiler['status'] == 'pass' and compiler['returncode'] == 0, 'parent compiler did not pass')
    for n, h in compiler['sources'].items():
        require(sha(local(ROOT, n)) == h, 'changed parent compiler source ' + n)
    return path, doc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    p.add_argument('--parent', type=Path)
    p.add_argument('--native', type=Path)
    p.add_argument('--eda', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS), 'evidence beneath runs required')
    a.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=a.mode + '-', dir=a.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    doc = dict(status='running', backend='eda' if a.mode == 'vcs' else 'f2',
               observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
               source_root=str(ROOT), sources=sources, commands=[],
               scope='atomic generated regional cut-control observation; original endpoint/router state remains separately owned',
               control_bits=75, staging_bits=146, physical_fpga_capture=False,
               full_image=False, CPU_migration_verified=False, staging_restore_supported=False)
    summary = out / 'summary.json'
    def save():
        summary.write_text(json.dumps(doc, indent=2) + '\n')
    def run(argv, name, *, cwd=out, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(out / (name + '.log')))
        doc['commands'].append(row)
        save()
        with Path(row['log']).open('x') as stream:
            r = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = r.returncode
        row['log_sha256'] = sha(row['log'])
        save()
        require(r.returncode == expected, 'inspect underlying compiler/runtime log ' + row['log'])
        return Path(row['log']).read_text()
    def native_input():
        require(a.native is not None, 'explicit native receipt required')
        np = local(ROOT, a.native)
        n = json.loads(np.read_text())
        require(n['status'] == 'pass' and n['backend'] == 'f2' and n['sources'] == sources,
                'native source or completion mismatch')
        for group in ('inputs', 'artifacts'):
            for name, h in n[group].items():
                require(sha(np.parent / name) == h, 'native evidence changed ' + name)
        parent, _ = check_parent(n['parent_receipt']['path'])
        require(sha(parent) == n['parent_receipt']['sha256'], 'changed parent selection')
        doc['native_receipt'] = dict(path=str(np), sha256=sha(np))
        return np, n
    save()
    print(out, flush=True)
    try:
        if a.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                    'native manager Vivado required')
            require(a.parent is not None, 'explicit original compiler/native parent required')
            parent_path, parent = check_parent(a.parent)
            doc['parent_receipt'] = dict(path=str(parent_path), sha256=sha(parent_path))
            for name in parent['inputs']:
                dest = out / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(parent_path.parent / name, dest)
            for name in SOURCES:
                dest = out / 'snapshot-sources' / Path(name).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            doc['regional_audit'] = audit_regions(out / 'generated')
            doc['cut_audit'] = audit_cut(out / 'generated')
            old_fixture = (parent_path.parent / 'sources/native_regions_fixture.sv').read_text()
            (out / 'sources/native_regions_fixture.sv').write_text(fixture(old_fixture))
            files = json.loads((out / 'files.json').read_text()) + [
                'snapshot-sources/' + Path(n).name for n in (RTL, STAGE)]
            (out / 'files.json').write_text(json.dumps(files, indent=2) + '\n')
            tcl = (parent_path.parent / 'synth.tcl').read_text()
            tcl = tcl.replace('read_verilog -sv ' + ' '.join(json.loads((parent_path.parent / 'files.json').read_text())),
                              'read_verilog -sv ' + ' '.join(files))
            tcl = tcl.replace('report_utilization -file utilization.rpt', '''set payload [get_cells snapshot/staging/payload_reg*]
if {[llength $payload] != 75} {error "incomplete atomic cut-control payload"}
set stage_regs [get_cells -hier -filter {NAME =~ snapshot/staging/* && REF_NAME =~ FD*}]
if {[llength $stage_regs] != 146} {error "incomplete whole staging owner"}
foreach cell $stage_regs {
  set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "staging owner clock was masked"}
}
puts "REGION_CUT_SNAPSHOT_SYNTH_PASS control_bits=75 staging_registers=146"
report_utilization -file utilization.rpt''')
            (out / 'synth.tcl').write_text(tcl)
            doc['inputs'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*')
                             if f.is_file() and f != summary}
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
            require('REGION_CUT_SNAPSHOT_SYNTH_PASS control_bits=75 staging_registers=146' in text and
                    not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native staging synthesis failed')
            doc['artifacts'] = {n: sha(out / n) for n in ('native-regions.dcp', 'utilization.rpt', 'timing.rpt', 'synth.log')}
        elif a.mode == 'vcs':
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and
                    toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 only')
            np, native = native_input()
            for name in native['inputs']:
                dest = out / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(np.parent / name, dest)
            files = json.loads((out / 'files.json').read_text())
            build = out / 'build'
            build.mkdir()
            def compile_variant(build_dir, file_list, name):
                run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate',
                     '-debug_access+all', '+incdir+' + str(out), '-top', 'native_region_cut_snapshot_tb',
                     '-top', 'glbl', '-Mdir=' + str(build_dir / 'csrc'), '-o', build_dir / 'simv',
                     *[out / n for n in file_list], out / 'BUFGCE.v', out / 'glbl.v',
                     out / 'snapshot-sources' / Path(TB).name, out / 'snapshot-sources' / Path(EXIT).name],
                    name, cwd=build_dir)
            compile_variant(build, files, 'compile')
            cases = [('healthy', [], 0)]
            cases += [(n, ['+snapshot-fault=' + n], 0) for n in
                      ('early-bank', 'early-snapshot', 'overlap', 'restage', 'busy-release')]
            cases += [(n, ['+' + n], 0) for n in ('missing-owner', 'ce-drift', 'cycle-drift',
                      'pending-owner', 'pending-ce', 'pending-cycle', 'release-owner', 'release-ce', 'release-cycle')]
            cases += [('corrupt-snapshot', ['+corrupt-snapshot'], 1)]
            doc['cases'] = {}
            for name, args, status in cases:
                work = out / name
                work.mkdir()
                text = run([build / 'simv', '-no_save', *args], name, cwd=work, expected=status)
                require(not re.search(r'Assertion failed|Fatal:|Error:', text), 'original runtime assertion ' + name)
                if name == 'healthy':
                    require('REGION_CUT_SNAPSHOT_PASS words=10 control_bits=75 staging_bits=146' in text and
                            'NATIVE_REGIONS_PASS' in text, 'healthy coverage incomplete')
                elif name == 'corrupt-snapshot':
                    require('atomic control serial word and zero padding before acknowledgement' in text and
                            'response_ack=0' in text, 'corruption failed at wrong boundary')
                else:
                    require(('REGION_CUT_SNAPSHOT_REJECT kind=' + name in text or
                             'NATIVE_REGIONS_REJECTED kind=' + name in text) and
                            'NATIVE_REGIONS_PASS' not in text, 'negative not rejected ' + name)
                doc['cases'][name] = audit_wave(work / 'native-regions.vcd', healthy=name == 'healthy',
                                               corrupt=name == 'corrupt-snapshot')
                save()
            # Corrupt the actual synthesized adapter's staging input in a
            # separately compiled negative executable. The expected-state
            # oracle and original control registers remain unchanged.
            original_rtl = 'snapshot-sources/' + Path(RTL).name
            mutated_rtl = 'snapshot-sources/CheckpointRegionCutSnapshot-corrupt.sv'
            text = (out / original_rtl).read_text()
            needle = '.live_state(live_control_state)'
            require(text.count(needle) == 1, 'ambiguous compiled semantic mutation')
            (out / mutated_rtl).write_text(text.replace(needle, ".live_state(live_control_state ^ 75'd1)"))
            broken = out / 'semantic-build'
            broken.mkdir()
            compile_variant(broken, [mutated_rtl if n == original_rtl else n for n in files], 'semantic-compile')
            work = out / 'compiled-control-corruption'
            work.mkdir()
            text = run([broken / 'simv', '-no_save'], 'compiled-control-corruption', cwd=work, expected=1)
            require('complete pre-edge cut and pending control vector' in text and 'response_ack=0' in text,
                    'compiled semantic corruption stopped at wrong boundary')
            doc['cases']['compiled-control-corruption'] = audit_wave(
                work / 'native-regions.vcd', semantic_corruption=True)
            doc['semantic_mutation'] = dict(path=str(out / mutated_rtl), sha256=sha(out / mutated_rtl),
                                            source_sha256=sha(out / original_rtl), bit=0)
            doc['auditor_mutations_rejected'] = []
            for bit in range(75):
                try:
                    audit_wave(out / 'healthy/native-regions.vcd', healthy=True, mutate_bit=bit)
                except FormatError:
                    doc['auditor_mutations_rejected'].append(bit)
                else:
                    raise FormatError('corrupt control bit escaped independent checker: ' + str(bit))
            doc['inputs'] = native['inputs']
            doc['artifacts'] = {str(f.relative_to(out)): sha(f) for f in out.rglob('*')
                                if f.is_file() and f.suffix in ('.log', '.vcd')}
            doc['artifacts'][mutated_rtl] = sha(out / mutated_rtl)
        else:
            np, native = native_input()
            ep = local(ROOT, a.eda)
            eda = json.loads(ep.read_text())
            require(eda['status'] == 'pass' and eda['backend'] == 'eda' and eda['sources'] == sources and
                    eda['native_receipt']['sha256'] == sha(np), 'native/EDA receipt mismatch')
            require(len(eda['cases']) == 17 and len(eda['auditor_mutations_rejected']) == 75,
                    'incomplete healthy/negative/raw-wave coverage')
            for name, h in eda['artifacts'].items():
                require(sha(ep.parent / name) == h, 'changed EDA evidence ' + name)
            doc['eda_receipt'] = dict(path=str(ep), sha256=sha(ep))
            doc['cases'] = eda['cases']
        require(all(sha(ROOT / n) == h for n, h in sources.items()), 'source changed during verification')
        doc['status'] = 'pass'
    except BaseException:
        doc['status'] = 'fail'
        raise
    finally:
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print(summary, flush=True)


if __name__ == '__main__':
    main()
