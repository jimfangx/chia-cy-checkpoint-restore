"""Native synthesized shared-bank readout of atomically staged shell state.

Component evidence only. All VCS execution is restricted to the EDA mirror.
The staging oracle uses original register probes, not the serialized vector.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.tests.verify_live_shell_snapshot import (
    ROOT, RUNS, NEGATIVES, audit_generated, audit_wave, sha, wave_rows,
)

BASE = 'sims/firesim/sim/midas/src/main/verilog/'
RESOURCES = [BASE + n for n in ('CheckpointNativeStateSnapshot.sv',
    'CheckpointLiveShellSnapshotReadout.sv', 'CheckpointSnapshotStateBank.sv')]
TB = 'tools/checkpoint_formats/tests/live_shell_bank_snapshot_tb.sv'
SOURCES = sorted({str(p.relative_to(ROOT)) for tree in (
    'sims/firesim/sim/midas/src/main/scala', 'sims/firesim/sim/midas/src/test/scala')
    for p in (ROOT / tree).rglob('*.scala')} | set(RESOURCES) | {TB,
    'tools/checkpoint_formats/tests/verify_live_shell_bank_readout.py',
    'tools/checkpoint_formats/tests/verify_live_shell_snapshot.py',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/toolchain.py', 'tools/checkpoint_formats/codec.py'})


def audit(directory, binding=None):
    doc = json.loads((directory / 'binding.json').read_text()) if binding is None else binding
    snapshot = json.loads((directory / 'snapshot-binding.json').read_text())
    mapping = json.loads((directory / 'banked-mapping.json').read_text())
    require(doc['readout_version'] == 1 and doc['scope'] ==
            'selected_live_shell_staged_payload_bank_readout_only', 'changed readout scope')
    require(doc['snapshot_binding_sha256'] == sha(directory / 'snapshot-binding.json') and
            doc['payload'] == snapshot and doc['payload_bits'] == snapshot['bits'], 'changed staged source')
    require(doc['wired_sha256'] == sha(directory / 'wired.fir') and
            doc['wired_annotations_sha256'] == sha(directory / 'wired.anno.json'), 'changed actual network')
    expected_id = hashlib.sha256(((directory / 'snapshot-binding.json').read_text() +
        '\nimmutable_live_shell_native_payload_lsb0').encode()).hexdigest()
    bank = max(r['bank'] for r in mapping['state']) + 1
    require(doc['entry'] == dict(state_id=expected_id, bank=bank, slot=0, width=64,
        depth=(snapshot['bits'] + 63) // 64), 'changed staged descriptor geometry or identity')
    require(doc['readout_owner_bits'] == 69 and doc['readout_owner'] ==
            'LiveTop.checkpoint_live_readout_adapter' and doc['readout_state_owner'] ==
            'unsupported_live_readout_state_capture_and_restore', 'omitted new live owner')
    for flag in ('complete_fpga_capture', 'deployable_capture_image',
                 'production_freeze_owners_bound', 'metasim_restore_supported'):
        require(doc[flag] is False, 'unproven production admission')
    descriptors = json.loads((directory / 'descriptors.json').read_text())
    require(descriptors['readout_binding'] == json.loads((directory / 'binding.json').read_text()) and
            descriptors['readout_binding_sha256'] == sha(directory / 'binding.json'), 'stale descriptor binding')
    require(descriptors['original_mapping'] == mapping, 'changed enclosing original owners')
    descriptor_binding = json.loads((directory / 'descriptor-binding.json').read_text())
    require(descriptor_binding['manifest'] == descriptors and descriptor_binding['manifest_sha256'] ==
            sha(directory / 'descriptors.json') and descriptor_binding['original_binding'] ==
            json.loads((directory / 'banked-binding.json').read_text()), 'stale generated host descriptor identity')
    for flag in ('complete_fpga_capture', 'deployable_capture_image', 'production_freeze_owners_bound',
                 'metasim_restore_supported', 'reserved_widget_descriptor_layout_installed'):
        require(descriptors[flag] is False and descriptor_binding[flag] is False, 'false production installation')
    expected = [dict(ordinal=i, state_id=r['state_id'], bank=r['bank'], slot=r['slot'],
                    width=r['transfer_width'], depth=r['transfer_depth'], domain='original_shell_storage')
                for i, r in enumerate(mapping['state'])]
    expected += [dict(ordinal=len(expected), domain='immutable_live_shell_and_native_payload', **doc['entry'])]
    require(descriptors['state'] == expected, 'original or appended descriptor omitted/changed')
    text = (directory / 'wired.fir').read_text()
    require('reader_idle <= and(and(checkpoint_shell_live_snapshot_raw_req_ready, not(checkpoint_shell_live_snapshot_raw_resp_valid)), checkpoint_live_readout_idle)' in text and
            'borrow_attempt <= checkpoint_live_readout_attempt' in text and
            'checkpoint_live_readout_adapter.clock <= clock' in text and
            'checkpoint_live_readout_adapter.permission <= checkpoint_shell_live_snapshot_borrow_enable' in text,
            'cut/idle/attempt/raw-clock binding changed')
    for path in RESOURCES[1:]:
        suffix = '.live-shell-bank-' + Path(path).name
        require(doc['files'][suffix] == sha(ROOT / path), 'stale synthesized readout source')
    return snapshot, doc['entry']


def bank_wave(path, snapshot, entry, corrupt=False, owner_bit=None):
    stage = 'dut.shell.checkpoint_shell_live_snapshot_adapter.'
    readout = 'dut.checkpoint_live_readout_adapter.'
    names = {'clock', 'request', 'ready', 'target_cycle', 'req_valid', 'req_ready', 'resp_valid',
             'resp_ready', 'response_data', 'resp_error', 'bank', 'slot', 'address', 'failed',
             'snapshot_reset', 'bank_reset', 'borrow_enable', 'value'}
    fields = snapshot['state'] + snapshot['native_state']
    def signal(row):
        return 'dut.shell.' + row['hierarchy'].split('.')[-1] + (
            '_pipe_0' if row.get('adapter') == 'firrtl-emitter-memory-pipeline-v1' else '')
    names |= {signal(r) for r in fields} | {stage + 'payload',
        'dut.checkpoint_live_readout_control_state'}
    owner_fields = ('pending', 'snapshot_owner', 'snapshot_bank.saved_data',
                    'snapshot_bank.saved_error', 'snapshot_bank.pending', 'snapshot_bank.failed')
    names |= {readout + n for n in owner_fields}
    previous = None
    payload = None
    pending = None
    accepted = acknowledged = staged = invalid = 0
    first = None
    for value in wave_rows(path, names):
        if any(v is None for v in value.values()):
            # The parser emits one empty sample before VCD's first timestamp.
            # As in the staging auditor, unknowns are permitted only until the
            # initialization reset is explicitly deasserted.
            require(value['snapshot_reset'] != 0, 'unknown initialized bus/state')
            previous = value
            continue
        if previous and previous['clock'] == 0 and value['clock'] == 1:
            p = previous
            if first is not None:
                require(not (p['req_valid'] and p['req_ready']) and
                        not (p['resp_valid'] and p['resp_ready']),
                        'bank edge acknowledged after first divergence')
            if p['bank_reset']:
                pending = None
            else:
                if p['request'] and p['ready']:
                    payload = sum((p[signal(r)] & ((1 << r['width']) - 1)) << r['offset'] for r in fields)
                if p['req_valid'] and p['req_ready']:
                    require(pending is None and p['borrow_enable'] and not p['failed'], 'overlap/unqualified bank request')
                    pending = (p['bank'], p['slot'], p['address'], payload)
                    accepted += 1
                if p['resp_valid'] and p['resp_ready']:
                    require(pending is not None and not p['failed'], 'unowned response acknowledgement')
                    pending = None
                    acknowledged += 1
        if not value['snapshot_reset'] and value['resp_valid']:
            require(pending is not None and value['borrow_enable'] and not value['failed'], 'response escaped epoch')
            bank, slot, address, packed = pending
            if bank == entry['bank']:
                bad = slot != 0 or address >= entry['depth']
                expected = 0 if bad else (packed >> (64 * address)) & ((1 << 64) - 1)
                if value['response_data'] != expected:
                    require(corrupt, 'staged bank response differs from independent preedge state')
                    if first is None:
                        first = dict(target_cycle=value['target_cycle'], word_address=address,
                                     expected=expected, actual=value['response_data'],
                                     functional_value=value['value'])
                require(value['resp_error'] == int(bad), 'invalid selector error mismatch')
                staged += 1
                invalid += int(bad)
        if value['failed']:
            require(not value['req_ready'] and not value['resp_valid'], 'fault acknowledged an edge')
        if first is not None:
            require(value['target_cycle'] == first['target_cycle'] and value['value'] == first['functional_value'],
                    'functional cut advanced after first divergence')
        if not value['bank_reset']:
            observed = value['dut.checkpoint_live_readout_control_state']
            if owner_bit is not None:
                observed ^= 1 << owner_bit
            expected_owner = (value[readout + 'pending'] | (value[readout + 'snapshot_owner'] << 1) |
                (value[readout + 'snapshot_bank.saved_data'] << 2) |
                (value[readout + 'snapshot_bank.saved_error'] << 66) |
                (value[readout + 'snapshot_bank.pending'] << 67) |
                (value[readout + 'snapshot_bank.failed'] << 68))
            require(observed == expected_owner, 'live readout control omitted a register bit')
        previous = value
    require(bool(first) == corrupt, 'missing/unexpected first divergence')
    return dict(accepted=accepted, acknowledged=acknowledged, staged_samples=staged,
                invalid_samples=invalid, first_divergence=first,
                acknowledgements_after_first_divergence=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=['vivado', 'vcs'], required=True)
    ap.add_argument('--generated', type=Path)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence must be under runs')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    receipt = dict(status='running', backend='f2' if args.mode == 'vivado' else 'eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT), host=socket.gethostname(),
        sources=sources, physical_fpga_capture=False, full_image=False, commands=[])
    def save():
        (out / 'summary.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(argv, name, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(log))
        receipt['commands'].append(row)
        with log.open('x') as stream:
            r = subprocess.run(row['argv'], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = r.returncode
        save()
        require(r.returncode == expected, 'inspect compiler/runtime log ' + str(log))
        return log.read_text()
    save()
    print(out, flush=True)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native manager only')
        require(args.generated is not None and args.native is None, 'generated fixture required')
        shutil.copytree(args.generated, out / 'generated')
        shutil.copytree(args.generated.parent / 'live-shell-native-snapshot', out / 'snapshot-generated')
        snapshot, entry = audit(out / 'generated')
        audit_generated(out / 'snapshot-generated')
        require((out / 'generated/snapshot.fir').read_bytes() ==
                (out / 'snapshot-generated/wired.fir').read_bytes(), 'snapshot fixture differs')
        negatives = []
        for case in ('bank', 'width', 'depth', 'id', 'payload', 'owner', 'restore', 'scope'):
            mutant = copy.deepcopy(json.loads((out / 'generated/binding.json').read_text()))
            if case in ('bank', 'width', 'depth'): mutant['entry'][case] += 1
            elif case == 'id': mutant['entry']['state_id'] = '0' * 64
            elif case == 'payload': mutant['payload_bits'] -= 1
            elif case == 'owner': mutant['readout_owner_bits'] -= 1
            elif case == 'restore': mutant['metasim_restore_supported'] = True
            else: mutant['scope'] = 'complete'
            try: audit(out / 'generated', mutant)
            except FormatError as error: negatives.append(dict(case=case, error=str(error)))
            else: raise FormatError('accepted schema mutation ' + case)
        receipt['schema_negatives'] = negatives
        for path in RESOURCES: shutil.copyfile(ROOT / path, out / Path(path).name)
        # Select original count and memory by original global owner identity.
        mapping = json.loads((out / 'generated/banked-mapping.json').read_text())['state']
        count = next(r for r in mapping if r['hierarchy'] == 'LiveTop.shell.count')
        memory = next(r for r in mapping if r['kind'] == 'memory')
        pipeline = next(r for r in mapping if r['hierarchy'] == 'LiveTop.shell.mem_r_addr')
        (out / 'bank-selector.svh').write_text(f"localparam COUNT_BANK=8'd{count['bank']}, COUNT_SLOT=16'd{count['slot']}, SNAPSHOT_BANK=8'd{entry['bank']}, PIPE_BANK=8'd{pipeline['bank']}, PIPE_SLOT=16'd{pipeline['slot']};\n")
        (out / 'native-geometry.svh').write_text(f"localparam BITS={snapshot['bits']}, WORDS={snapshot['words']};\n" +
            f"localparam MEM_BANK=8'd{memory['bank']}, MEM_SLOT=16'd{memory['slot']};\n")
        terms = ['dut.shell.' + r['hierarchy'].split('.')[-1] + (
            '_pipe_0' if r['adapter'] == 'firrtl-emitter-memory-pipeline-v1' else '') for r in snapshot['native_state']]
        (out / 'native-probes.svh').write_text('wire [BITS-238:0] native_probes={' + ','.join(reversed(terms)) + '};\n')
        (out / 'synth.tcl').write_text('''set_param general.maxThreads 4
read_verilog -sv {generated/wired.sv CheckpointNativeStateSnapshot.sv CheckpointLiveShellSnapshotReadout.sv CheckpointSnapshotStateBank.sv}
synth_design -top LiveTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -keep_equivalent_registers
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set staged [get_cells -hier -filter {NAME =~ */checkpoint_shell_live_snapshot_adapter/* && IS_SEQUENTIAL == 1}]
set readout [get_cells -hier -filter {NAME =~ checkpoint_live_readout_adapter/* && IS_SEQUENTIAL == 1}]
if {[llength $staged] != STAGE} {error "incomplete staging owner"}
if {[llength $readout] != 69} {error "incomplete live readout owner"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force live-shell-bank-readout.dcp
puts "LIVE_SHELL_BANK_SYNTH_PASS staging=[llength $staged] readout=[llength $readout]"
'''.replace('STAGE', str(snapshot['staging_owner_bits'])))
        receipt['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p.name != 'summary.json'}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require('LIVE_SHELL_BANK_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native synthesis failed')
    else:
        require(str(ROOT).startswith('/scratch/') and toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 only')
        require(args.native is not None and args.generated is None, 'native receipt required')
        native = json.loads((args.native / 'summary.json').read_text())
        require(native['status'] == 'pass' and native['sources'] == sources, 'stale native sources')
        for group in ('inputs', 'artifacts'):
            for name, h in native[group].items(): require(sha(args.native / name) == h, 'changed native artifact ' + name)
        for name in native['inputs']:
            p = out / name; p.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.native / name, p)
        receipt['inputs'] = native['inputs']
        snapshot, entry = audit(out / 'generated')
        shutil.copyfile(ROOT / TB, out / 'testbench.sv')
        audits = {}
        for mode in ('healthy', 'payload', 'native-payload'):
            folder = out / mode; folder.mkdir()
            source = (out / 'CheckpointSnapshotStateBank.sv').read_text()
            if mode != 'healthy':
                needle = "invalid ? 64'b0 : padded[address * 64 +: 64]"
                require(source.count(needle) == 1, 'ambiguous corruption site')
                address = 0 if mode == 'payload' else snapshot['original_live_bits'] // 64
                mask = 1 if mode == 'payload' else 1 << (snapshot['original_live_bits'] % 64)
                source = source.replace(needle, f"invalid ? 64'b0 : (padded[address * 64 +: 64] ^ (address == 32'd{address} ? 64'h{mask:x} : 64'b0))")
            (folder / 'compiled-bank.sv').write_text(source)
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                 '+incdir+' + str(out), '-top', 'live_shell_snapshot_tb', '-Mdir=' + str(folder / 'csrc'), '-o', folder / 'simv',
                 out / 'generated/wired.sv', out / 'CheckpointNativeStateSnapshot.sv',
                 out / 'CheckpointLiveShellSnapshotReadout.sv', folder / 'compiled-bank.sv', out / 'testbench.sv',
                 ROOT / 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'], mode + '-compile')
            cases = ('healthy', *NEGATIVES, 'busy-reader-capture', 'busy-reader-release',
                     'staged-busy-release', 'staged-lost-freeze', 'staged-drift', 'staged-early-read', 'staged-sameedge-read') if mode == 'healthy' else ('payload',)
            for case in cases:
                label = case if mode == 'healthy' else mode
                text = run([folder / 'simv', '-no_save', '+CASE=' + case], label + '-run', 0 if mode == 'healthy' else 1)
                wave = out / (label + '.vcd'); (out / 'live-shell-snapshot.vcd').rename(wave)
                audits[label] = bank_wave(wave, snapshot, entry, mode != 'healthy')
                if mode != 'healthy':
                    require('signal=immutable staged bank response' in text and 'LIVE_SHELL_SNAPSHOT_PASS' not in text,
                            'corruption did not stop before response acknowledgement')
                    first = audits[label]['first_divergence']
                    require(first['target_cycle'] == 0 and first['word_address'] == (0 if mode == 'payload' else 3) and
                            audits[label]['accepted'] == audits[label]['acknowledged'] + 1, 'incorrect first divergence/ack count')
                elif case == 'healthy':
                    match = re.search(r'LIVE_SHELL_SNAPSHOT_PASS checks=(\d+) cuts=4 reads=68 stalls=32', text)
                    require(match and audits[label]['accepted'] == audits[label]['acknowledged'] == 68, 'incomplete shared bus workload')
                    receipt['checks'] = int(match[1])
                    receipt['staging_wave'] = audit_wave(wave, snapshot)
                else: require('LIVE_SHELL_SNAPSHOT_NEGATIVE_PASS scenario=' + case in text, 'missing negative test pass')
        receipt['wave_audits'] = audits
        rejected = []
        for bit in range(69):
            try: bank_wave(out / 'healthy.vcd', snapshot, entry, owner_bit=bit)
            except FormatError: rejected.append(bit)
            else: raise FormatError('accepted readout owner bit mutation ' + str(bit))
        receipt['readout_owner_mutations_rejected'] = rejected
        receipt['native_receipt'] = dict(path=str(args.native / 'summary.json'), sha256=sha(args.native / 'summary.json'))
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, 'sources changed during verification')
    receipt.update(status='pass', artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and
        (p.suffix in {'.log', '.vcd', '.rpt', '.dcp'} or p.name == 'simv')})
    save(); print(out / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
