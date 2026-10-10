"""Audit a fresh paired FCFS invocation without consulting a reused build.

This is the complete pre-edge M6 prerequisite audit, not live-shadow acceptance.
The invocation must archive the native Make metadata beside its executable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from tools.checkpoint_formats.aggregate import build_identity
from tools.checkpoint_formats.aggregate_packed import decode_aggregate
from tools.checkpoint_formats.bridge_semantic import audit_bridge_mapping, audit_erased_boundary_outputs, read_snapshot
from tools.checkpoint_formats.codec import canonical, require, unique_object
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    require(Path(path).is_file(), 'missing archived evidence: ' + str(path))
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def audit_native_archive(out):
    """Bind all native inputs, inventories, executable and every image record."""
    out = Path(out)
    metadata = out / 'production-build-metadata'
    inputs, runtime, generated, layout, archived_build = [load(metadata / (name + '.json')) for name in
        ('native-build-inputs', 'runtime-manifest', 'generated-manifest', 'harness-layout', 'aggregate-build')]
    require(inputs['compiler'] == '/usr/bin/g++-13'
            and inputs['vcs_home'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1'
            and inputs['make_profile'] == 'fcfs-fased-v1', 'unaudited production toolchain/profile')
    require(hashlib.sha256(canonical(inputs)).hexdigest() == runtime['native_build_hash']
            and inputs['generated_build'] == layout['generated_build_hash'], 'native metadata binding mismatch')
    require(bool(inputs['sources']), 'missing native source bindings')
    for name, digest in inputs['sources'].items():
        path = ROOT / name
        require(path.is_file() and sha(path) == digest, 'native source changed/missing: ' + name)
    executable = out / 'AXI4Fuzzer-checkpoint'
    require(executable.is_file(), 'missing archived production executable')
    build = build_identity(runtime, generated, layout, executable)
    require(build == archived_build, 'archived executable/inventory binding mismatch')
    cut = decode_aggregate((out / 'capture.fsckpt').read_bytes(), build, runtime, generated, layout)
    return runtime, generated, layout, cut


def audit(out, preservation):
    out, preservation = Path(out).resolve(), Path(preservation).resolve()
    summary = load(out / 'summary.json')
    source_inputs = load(out / 'source-inputs.json')
    require(bool(source_inputs), 'missing semantic source/artifact bindings')
    for name, digest in source_inputs.items():
        path = Path(name)
        require(path.is_file() and sha(path) == digest, 'semantic source/artifact changed: ' + name)
    runtime, generated, layout, cut = audit_native_archive(out)
    require(len(runtime['native_owners']) == 17 and len(layout['records']) == 29
            and sum(e['depth'] for e in generated['state']) == 13507456,
            'partial FCFS Level-1 inventory')
    native_cycle = cut['target_cycle']
    del cut
    manifest, boundary = [load(out / ('FireSim-generated' + suffix)) for suffix in
                          ('.semantic-state.json', '.semantic-boundary.json')]
    mapping = load(out / 'probe/mapping.json')
    require(generated == load(out / 'FireSim-generated.simulator-state.json'),
            'archived native and independently emitted inventories differ')
    independent_mapping = audit_bridge_mapping(manifest, boundary,
        (out / 'FireSim-generated.semantic-reference.fir').read_text(),
        (out / 'FireSim-generated.semantic-clean.sv').read_text(), generated,
        (out / 'FireSim-generated.simulator-reference.fir').read_text(),
        (out / 'FireSim-generated.sv').read_text(),
        (ROOT / 'sims/firesim/sim/midas/src/main/verilog/BUFGCE.v').read_text(),
        'FPGATop.sim.target.AXI4Fuzzer_.fuzzer_')
    require(independent_mapping == mapping, 'independent complete state/boundary mapping differs')
    erased_boundary = audit_erased_boundary_outputs(boundary,
        (out / 'FireSim-generated.semantic-reference.fir').read_text(),
        (out / 'FireSim-generated.semantic-clean.sv').read_text(),
        (out / 'FireSim-generated.sv').read_text(), mapping)
    require(erased_boundary == load(out / 'erased-boundary-audit.json')
            and len(erased_boundary['erased_outputs']) == 7 and len(erased_boundary['unresolved_inputs']) == 4,
            'erased boundary audit changed/incomplete')
    build, _ = builds(manifest, boundary, 'AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config')
    image = decode_semantic((out / 'capture.rtlckpt').read_bytes(), build, manifest)
    origin, original = read_snapshot(out / 'probe/captured.jsonl', manifest, mapping)
    semantic_cycle = origin['observed_target_edges']
    require(native_cycle == origin['target_cycle'] == 524402 and semantic_cycle == 524453
            and image['target_cycle'] == semantic_cycle and len(image['records']) == 1543,
            'wrong paired cut or cycle origin')
    require(sum(e['depth'] for e in manifest['state']) == 13503308,
            'partial FCFS semantic inventory')
    sidecar = load(out / 'capture.rtlckpt.cut.json')
    require(sidecar['level1_fased_cycle'] == native_cycle and sidecar['semantic_cycle'] == semantic_cycle
            and sidecar['checkpoint_sha256'] == sha(out / 'capture.rtlckpt')
            and sidecar['mapping_sha256'] == origin['mapping_sha256']
            and sidecar['live_cycle_alignment_verified'] is False, 'incorrect semantic cut sidecar')
    for name, expected_cycle in [('probe/restored.jsonl', native_cycle),
                                 ('clean/verified-readback.jsonl', semantic_cycle)]:
        observed, records = read_snapshot(out / name, manifest, mapping)
        require(observed['observed_target_edges'] == 0 and observed['target_cycle'] == expected_cycle
                and records == original, 'full pre-edge state/cycle mismatch: ' + name)
        del records
    require(image['records'] == original, 'independent hardware readout differs from semantic image')
    del image
    fault_header, fault = read_snapshot(out / 'clean/corrupted-readback.jsonl', manifest, mapping)
    require(fault_header['observed_target_edges'] == 0 and fault_header['target_cycle'] == semantic_cycle,
            'corruption readback advanced time or has wrong cycle')
    changes = [(e, a, b) for e, a, b in zip(manifest['state'], original, fault) if a != b]
    require(len(changes) == 1 and changes[0][0]['hierarchy'].endswith('.fuzzer.num_resps')
            and int(changes[0][1]['values'][0], 16) ^ int(changes[0][2]['values'][0], 16) == 1,
            'wrong actual clean-state single-bit corruption')
    del fault
    selected = {e['hierarchy']: r for e, r in zip(manifest['state'], original)}
    for path, value in [('fuzzer.num_reqs', 9996), ('fuzzer.num_resps', 10000), ('model.wipeIndex', 524288)]:
        require(int(selected['AXI4Fuzzer.fuzzer_.' + path]['values'][0], 16) == value,
                'paired cut lacks initialized/outstanding traffic')
    del original, selected
    pids = []
    for name in ('capture.log', 'restore.log', 'clean/run.log', 'clean/corruption.log'):
        text = (out / name).read_text()
        require(text.endswith('exit=0\n'), 'failed fresh VCS process: ' + name)
        pids.append(next(line for line in text.splitlines() if line.startswith('fresh_process_pid=')))
        if name.startswith('clean/'):
            require(f'BRIDGE_CLEAN_READBACK cycle={semantic_cycle} words=13503308 target_edges=0' in text,
                    'clean process omitted complete pre-edge readback')
        else:
            require('*** PASSED *** after 774628 cycles' in text, 'native continuation did not complete')
    require(len(set(pids)) == 4, 'fresh process identities are not distinct')
    restore = (out / 'restore.log').read_text()
    require('PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in restore
            and 'PRODUCTION_BOOTSTRAP zero_edges=1' in restore, 'public fresh restore omitted zero-edge bootstrap')
    plan_bindings = dict(line.split(maxsplit=1)[::-1] for line in
                         (preservation / 'plan-input-sha256.txt').read_text().splitlines())
    require(set(plan_bindings) == {'plan_agent.md', 'plan_human.md'}, 'incomplete plan preservation baseline')
    for name, digest in plan_bindings.items():
        require(sha(ROOT / name) == digest, 'read-only plan input changed: ' + name)
    require(subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, text=True).splitlines()
            == (preservation / 'staged-start.txt').read_text().splitlines(), 'staging changed')
    require(summary['live_shadow_acceptance'] is False and summary['live_cycle_alignment_verified'] is False
            and summary['live_boundary_adapter_complete'] is False
            and len(summary['missing_transformed_ports']) == 11, 'live acceptance overclaim')
    return dict(status='pass', milestone_status='in_progress', level1_cycle=native_cycle,
                semantic_cycle=semantic_cycle, semantic_entries=1543, semantic_words=13503308,
                level1_generated_words=13507456, harness_records=29, native_owners=17,
                fresh_processes=4, actual_outstanding_requests=4,
                complete_fresh_level1_and_clean_state_readback=True,
                pre_edge_single_bit_corruption_detected=True, live_shadow_acceptance=False,
                erased_output_definitions_verified=7, unresolved_boundary_inputs=erased_boundary['unresolved_inputs'],
                plans_preserved=True, staging_preserved=True, output=str(out),
                level1_sha256=sha(out / 'capture.fsckpt'), level2_sha256=sha(out / 'capture.rtlckpt'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='exact paired invocation directory')
    parser.add_argument('--preservation', type=Path, required=True, help='iteration plan/staging baseline directory')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.out, args.preservation)
    args.report.write_bytes(canonical(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
