"""Full FCFS semantic cut beside public Level-1 capture/fresh VCS restore.

The clean process verifies every semantic word before any target edge. Live
boundary synchronization is still unsupported; this is an M6 prerequisite.
Source both repository environments and vcs-env.sh LAST before invoking.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.aggregate import build_identity
from tools.checkpoint_formats.aggregate_packed import decode_aggregate
from tools.checkpoint_formats.bridge_semantic import (
    audit_bridge_mapping, audit_erased_boundary_outputs, prepare_paired_probe, package_snapshot,
    prepare_clean_readback, read_snapshot, read_boundary_inputs,
)
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


CONFIGURATION = 'AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--live', action='store_true', help='also run restored schema-2 lockstep and state corruption')
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    print('BRIDGE_SEMANTIC_VCS_OUTPUT ' + str(out), flush=True)
    (args.out / 'latest.json').write_bytes(canonical(dict(output=str(out))))
    make = ['make', 'TARGET_PROJECT=fasedtests', 'DESIGN=AXI4Fuzzer', 'TARGET_CONFIG=FCFSConfig',
            'PLATFORM_CONFIG=FCFS16GBQuadRank_DefaultF1Config',
            'SEMANTIC_BRIDGE_CHECKPOINT_ROOT=AXI4Fuzzer.fuzzer_', 'SIMULATOR_CHECKPOINT_INVENTORY=FPGATop',
            f'BUILD_DIR={args.build.resolve()}']
    run(make + ['verilog'], out / 'elaboration.log', ROOT / 'sims/firesim/sim')
    generated = args.build.resolve() / ('f2/f2-fasedtests-' + CONFIGURATION)
    base = generated / 'FireSim-generated'
    def path(suffix):
        return Path(str(base) + suffix)
    def document(suffix):
        return json.loads(path(suffix).read_text())
    manifest, boundary, inventory = [document(suffix) for suffix in
                                   ('.semantic-state.json', '.semantic-boundary.json', '.simulator-state.json')]
    bufgce = ROOT / 'sims/firesim/sim/midas/src/main/verilog/BUFGCE.v'
    mapping = audit_bridge_mapping(manifest, boundary, path('.semantic-reference.fir').read_text(),
                                   path('.semantic-clean.sv').read_text(), inventory,
                                   path('.simulator-reference.fir').read_text(), path('.sv').read_text(),
                                   bufgce.read_text(), 'FPGATop.sim.target.AXI4Fuzzer_.fuzzer_')
    erased_boundary = audit_erased_boundary_outputs(boundary, path('.semantic-reference.fir').read_text(),
                        path('.semantic-clean.sv').read_text(), path('.sv').read_text(), mapping)
    require(not erased_boundary['unresolved_inputs'], 'authoritative boundary inputs were erased')
    (out / 'erased-boundary-audit.json').write_bytes(canonical(erased_boundary))
    require(mapping['semantic_entries'] == 1543 and mapping['semantic_words'] == 13503308,
            'unexpected full FCFS semantic inventory')
    probe = out / 'probe'
    prepare_paired_probe(manifest, mapping, probe)
    live = out / 'live'
    if args.live:
        from tools.checkpoint_formats.bridge_live_shadow import prepare_bridge_authority
        prepare_bridge_authority(manifest, boundary, mapping, erased_boundary, live)
    source_files = [ROOT / 'tools/checkpoint_formats/bridge_semantic.py', Path(__file__),
                    ROOT / 'tools/checkpoint_formats/tests/audit_bridge_semantic.py',
                    ROOT / 'tools/checkpoint_formats/semantic_restore.cc', bufgce,
                    *[path(suffix) for suffix in ('.semantic-state.json', '.semantic-boundary.json',
                                                 '.semantic-reference.fir', '.semantic-clean.sv',
                                                 '.simulator-state.json', '.simulator-reference.fir', '.sv')],
                    *[ROOT / 'sims/firesim' / name for name in
                      ('sim/make/goldengate.mk',
                       'sim/midas/src/main/scala/midas/checkpoint/SemanticStateInventory.scala',
                       'sim/midas/src/main/scala/midas/passes/MidasTransforms.scala',
                       'sim/midas/src/main/scala/midas/stage/GoldenGateCli.scala')]]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    extra_verilog = str(probe / 'paired-probe.sv')
    extra_driver = []
    if args.live:
        extra_verilog += ' ' + str(live / 'authority.sv')
        transport = ROOT / 'tools/checkpoint_formats/live_shadow_transport.cc'
        extra_driver = ['FS_CHECKPOINT_SHADOW=1']
        hashes.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            transport, ROOT / 'tools/checkpoint_formats/bridge_live_shadow.py',
            ROOT / 'tools/checkpoint_formats/tests/verify_bridge_live_vcs.py', live / 'authority.sv']})
    (out / 'source-inputs.json').write_bytes(canonical(hashes))
    run(make + ['FS_CHECKPOINT_PROFILE=fcfs-fased-v1', 'VCS_FLAGS=-Mupdate',
                f'VCS={os.environ["VCS_HOME"]}/bin/vcs -full64', f'VCS_EXTRA_V={extra_verilog}', *extra_driver, 'vcs'],
        out / 'metasim-build.log', ROOT / 'sims/firesim/sim')
    executable = generated / 'checkpoint-vcs/AXI4Fuzzer-checkpoint'
    shutil.copy2(executable, out / executable.name)
    shutil.copytree(Path(str(executable) + '.daidir'), out / (executable.name + '.daidir'))
    for library in executable.parent.glob('*.so'):
        shutil.copy2(library, out / library.name)
    # Archive the metadata produced by THIS Make invocation, beside the copied
    # executable. Auditing a later/reused checkpoint-native directory can bind
    # the image to a different binary or silently lose its native provenance.
    metadata = out / 'production-build-metadata'
    shutil.copytree(generated / 'checkpoint-native', metadata)
    native_inputs, runtime, native_generated, layout = [
        json.loads((metadata / (name + '.json')).read_text()) for name in
        ('native-build-inputs', 'runtime-manifest', 'generated-manifest', 'harness-layout')]
    require(native_inputs['vcs_home'] == os.environ['VCS_HOME']
            and native_inputs['compiler'] == os.environ['CXX']
            and hashlib.sha256(canonical(native_inputs)).hexdigest() == runtime['native_build_hash']
            and native_generated == inventory, 'Make metadata does not bind this production inventory/build')
    native_build = build_identity(runtime, native_generated, layout, out / executable.name)
    (metadata / 'aggregate-build.json').write_bytes(canonical(native_build))
    # Include all exported metadata, libraries and the actual executable in
    # the source/artifact binding checked after the complete fresh-process run.
    hashes.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   [out / executable.name, *metadata.iterdir(), *out.glob('*.so'),
                    *(out / (executable.name + '.daidir')).rglob('*.so')] if p.is_file()})
    (out / 'source-inputs.json').write_bytes(canonical(hashes))
    for suffix in ('.semantic-state.json', '.semantic-boundary.json', '.semantic-reference.fir', '.semantic-clean.sv',
                   '.simulator-state.json', '.simulator-reference.fir', '.sv'):
        shutil.copy2(path(suffix), out / path(suffix).name)
        archived = out / path(suffix).name
        hashes[str(archived)] = hashlib.sha256(archived.read_bytes()).hexdigest()
    for archived in (probe / 'paired-probe.sv', probe / 'mapping.json', out / 'erased-boundary-audit.json'):
        hashes[str(archived)] = hashlib.sha256(archived.read_bytes()).hexdigest()
    (out / 'source-inputs.json').write_bytes(canonical(hashes))
    common = [out / executable.name, '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    image = out / 'capture.fsckpt'
    text = run(common + [f'+fs-checkpoint={image}', '+fs-checkpoint-operation=699275'],
               out / 'capture.log', out)
    require('*** PASSED ***' in text and 'PAIRED_SEMANTIC_SNAPSHOT' in text and image.is_file(),
            'public Level-1 capture/semantic observation failed')
    capture_header, capture_records = read_snapshot(probe / 'captured.jsonl', manifest, mapping)
    captured_inputs = read_boundary_inputs(probe / 'boundary-captured.json', mapping,
                                          capture_header['target_cycle'], capture_header['observed_target_edges'])
    native_cut = decode_aggregate(image.read_bytes(), native_build, runtime, native_generated, layout)
    require(native_cut['target_cycle'] == capture_header['target_cycle'],
            'independent semantic observation and public Level-1 capture differ in cut label')
    del native_cut
    require(524288 < capture_header['target_cycle'] < 774628, 'paired cut lacks initialized active target state')
    before = hashlib.sha256(image.read_bytes()).hexdigest()
    text = run(common + [f'+fs-restore={image}'], out / 'restore.log', out)
    require('*** PASSED ***' in text and 'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text
            and 'PRODUCTION_BOOTSTRAP zero_edges=1' in text, 'fresh public Level-1 continuation failed')
    restored_header, restored_records = read_snapshot(probe / 'restored.jsonl', manifest, mapping)
    require(read_boundary_inputs(probe / 'boundary-restored.json', mapping, restored_header['target_cycle'], 0)
            == captured_inputs, 'fresh Level-1 authoritative boundary inputs differ at the paired cut')
    require(restored_header['target_cycle'] == capture_header['target_cycle']
            and restored_header['observed_target_edges'] == 0 and restored_records == capture_records,
            'fresh Level-1 semantic state differs from independent Level-2 cut')
    require(hashlib.sha256(image.read_bytes()).hexdigest() == before, 'Level-1 image was modified')
    del restored_records, capture_records
    level2 = out / 'capture.rtlckpt'
    package_snapshot(probe / 'captured.jsonl', manifest, boundary, mapping, CONFIGURATION, level2)
    clean = out / 'clean'
    semantic_cycle = prepare_clean_readback(level2.read_bytes(), manifest, boundary, mapping, CONFIGURATION, clean)
    bench = (clean / 'clean.sv').read_text().replace(
        '// BRIDGE_READBACK_VERIFICATION_INJECTION',
        'if($test$plusargs("bridge-corrupt-state")) begin\n'
        '    dut.fuzzer.num_resps = dut.fuzzer.num_resps ^ 14\'h1;\n'
        '    $display("BRIDGE_INJECT_STATE cycle=' + str(semantic_cycle) + ' signal=fuzzer.num_resps");\n'
        '  end\n  #1;')
    (clean / 'clean.sv').write_text(bench)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    run([vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         '-CFLAGS', '-std=c++17', '-timescale=1ns/1ps', '-top', 'bridge_clean_tb', f'-Mdir={clean / "csrc"}',
         '-o', clean / 'simv', out / 'FireSim-generated.semantic-clean.sv', clean / 'clean.sv',
         ROOT / 'tools/checkpoint_formats/semantic_restore.cc'], clean / 'build.log')
    text = run([clean / 'simv', '+vcs+initreg+0', '+vcs+initmem+0'], clean / 'run.log', clean)
    require(f'BRIDGE_CLEAN_READBACK cycle={semantic_cycle} words=13503308 target_edges=0' in text,
            'clean semantic load/readback advanced a target edge')
    _, clean_records = read_snapshot(clean / 'readback.jsonl', manifest, mapping)
    _, captured_records = read_snapshot(probe / 'captured.jsonl', manifest, mapping)
    require(clean_records == captured_records, 'complete clean semantic pre-edge readback differs')
    shutil.copy2(clean / 'readback.jsonl', clean / 'verified-readback.jsonl')
    del clean_records
    text = run([clean / 'simv', '+vcs+initreg+0', '+vcs+initmem+0', '+bridge-corrupt-state'],
               clean / 'corruption.log', clean)
    require('BRIDGE_INJECT_STATE' in text and f'BRIDGE_CLEAN_READBACK cycle={semantic_cycle} '
            'words=13503308 target_edges=0' in text, 'actual clean-state corruption or zero-edge guard missing')
    _, corrupted_records = read_snapshot(clean / 'readback.jsonl', manifest, mapping)
    changed = [(e, a, b) for e, a, b in zip(manifest['state'], captured_records, corrupted_records) if a != b]
    require(len(changed) == 1 and changed[0][0]['hierarchy'].endswith('.fuzzer.num_resps')
            and int(changed[0][1]['values'][0], 16) ^ int(changed[0][2]['values'][0], 16) == 1,
            'independent complete readback failed to identify the actual single-bit state fault')
    shutil.copy2(clean / 'readback.jsonl', clean / 'corrupted-readback.jsonl')
    del corrupted_records, captured_records
    require(all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in hashes.items()),
            'semantic source inputs changed during verification')
    summary = dict(semantic_entries=mapping['semantic_entries'], semantic_words=mapping['semantic_words'],
                   cut=capture_header, independent_level2_image=str(level2), level1_image=str(image),
                   semantic_cycle=semantic_cycle, live_cycle_alignment_verified=False,
                   fresh_level1_semantic_words_compared=mapping['semantic_words'],
                   clean_pre_edge_words_compared=mapping['semantic_words'],
                   pre_edge_corruption_detected=dict(signal='fuzzer.num_resps', cycle=semantic_cycle, target_edges=0),
                   level1_restore_integrated=True, live_boundary_adapter_complete=False,
                   missing_transformed_ports=mapping['missing_transformed_ports'],
                   erased_output_semantics_verified=len(erased_boundary['erased_outputs']),
                   authoritative_boundary_input_bindings=mapping['boundary_input_bindings'],
                   authoritative_boundary_input_values=captured_inputs,
                   unresolved_boundary_inputs=erased_boundary['unresolved_inputs'],
                   live_shadow_acceptance=False, output=str(out))
    (out / 'summary.json').write_bytes(canonical(summary))
    print(json.dumps(summary, indent=2), flush=True)
    if args.live:
        from tools.checkpoint_formats.tests.verify_bridge_live_vcs import verify_live
        verify_live(out, manifest, boundary, mapping, erased_boundary, CONFIGURATION)


if __name__ == '__main__':
    main()
