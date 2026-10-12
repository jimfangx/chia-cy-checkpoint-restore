"""Finalize real production queue evidence using an explicit independent audit pair.

Local proofs cannot authorize production gate restore. Revalidate every retained
proof, negative control, complete audit, regression and protected input before
publishing a full-path artifact catalog. Extra retry directories are diagnostic.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.evidence import artifact_catalog, audit_pair, file_sha, selected_audit_pair
from tools.checkpoint_formats.production_dut import audit_architecture
from tools.checkpoint_formats.production_memory import audit as audit_memory
from tools.checkpoint_formats.production_queue import audit, reconstruct, validate_proof
from tools.checkpoint_formats.tests.verify_production_queue import negative_binding

parser = argparse.ArgumentParser(description=__doc__)
for name in ('evidence', 'checks', 'audit-pair', 'out'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--iteration', type=int, required=True)
parser.add_argument('--python-tests', type=int, required=True)
parser.add_argument('--python-test-log', type=Path)
args = parser.parse_args()
HERE, CHECKS, OUT = (p.resolve() for p in (args.evidence, args.checks, args.out))
OUT.mkdir(parents=True, exist_ok=True)
PRODUCTION = ROOT / 'automations/checkpoint_loop/runs/m10-iteration69/production/invocation-8yp22x6s'
ARCHITECTURE = PRODUCTION / 'architecture'
EVIDENCE = HERE / 'synthesis-model-audit'

def read(path):
    return json.loads(Path(path).read_text())

candidate = audit_architecture(ARCHITECTURE)
binding = reconstruct(ARCHITECTURE, EVIDENCE)
# Verification retries update selection.json. The explicitly bound independent
# audit pair owns the proof identity; never borrow a different latest proof.
proof_run, selected_audits = selected_audit_pair(args.audit_pair)
proof = proof_run / 'positive'
positive = audit(ARCHITECTURE, EVIDENCE, proof)
require(positive['retained_modules'] == 165 and positive['register_bits'] == 1135 and
        positive['assertions_proven'] == 2712 and positive['covers'] == 6276 and
        not positive['unproven_obligations']['register'] and not positive['unproven_obligations']['memory_port'] and
        len(positive['unproven_obligations']['output']) == 304 and positive['remaining_state_entries'] == 883,
        'production queue proof scope incomplete')
require(binding['semantic_register_bits'] == 8261 and binding['physical_register_bits'] == 7256 and
        len(binding['physical_storage_obligations']) == 7457 and
        sum(s['width'] * s['depth'] for s in binding['physical_storage_obligations']) == 102992412 and
        all(s['proof_status'] == 'unproven' for s in binding['physical_storage_obligations']),
        'complete physical obligations missing or falsely proven')
commands = read(proof_run / 'commands.json')
require(len(commands) == 9 and all(c['exit_code'] == 0 and c['argv'][0] in (
        '/ecad/tools/cadence/JASPER/jasper_2025.03/bin/jg',
        str(ROOT / 'automations/checkpoint_loop/jasper-limited.sh')) and
        c['argv'][1:4] == ['-allow_unsupported_OS', '-batch', '-tcl'] for c in commands),
        'retained complete CAD scope missing')
saved = read(proof_run / 'summary.json')
require(len(saved['fresh_negative_proofs']) == 8 and saved['status'] == 'in_progress' and
        not saved['formal_state_map_complete'] and not saved['gate_restore_authorized'], 'wrong proof authorization')
for name in ('Queue_2', 'Queue_39'):
    for kind in ('polarity', 'missing_register', 'write_enable', 'read_address'):
        value, prop = negative_binding(binding, name, kind)
        result = validate_proof(value, proof_run / 'negative' / name / kind)
        category = 'register' if kind == 'polarity' else 'memory_port'
        require(prop in result['unproven_obligations'][category], 'retained false relationship missing counterexample')
audits = []
for report_path, report in selected_audits:
    directory = report_path.parent
    require(report['status'] == 'passed' and report['actual_artifact_mutations_rejected'] == 24 and
            report['unchanged_control_audits'] == 2 and len(report['independent_fresh_negative_audits']) == 8 and
            report['original_proofs_unchanged'] and report['incomplete_map_loader_rejections'] ==
            {'binding': 'invalid ASIC state map', 'audited_local_proof': 'incomplete formal build artifacts'},
            'independent queue audit incomplete')
    require(read(directory / 'independent-audit.json') == positive,
            'selected independent audit differs from current proof reconstruction')
    require(all(file_sha(p) == h for p, h in report['original_proof_hashes'].items()), 'original CAD evidence changed')
    obligations = read(directory / 'unproven-composition-obligations.json')
    require(obligations['semantic_state'] == candidate['entries'] and
            obligations['physical_storage'] == binding['physical_storage_obligations'] and
            obligations['boundary_manifest'] == read(ARCHITECTURE / 'boundary.json') and
            obligations['boundary_manifest_sha256'] == binding['boundary_manifest_sha256'] and
            not obligations['formal_state_map_complete'] and not obligations['gate_restore_authorized'],
            'complete unproven composition inventory differs')
    require(len(report['rejections']) == 24 and
            all(Path(r['artifacts']).resolve() == directory / 'mutations' / name and
                (Path(r['artifacts']) / 'binding.json').is_file() and r['rejected']
                for name, r in report['rejections'].items()),
            'actual independent mutation artifact missing or borrowed from another audit')
    audits.append(str(directory / 'summary.json'))
require(len(audits) == 2, 'two complete independent queue audit passes required')
require(all(r['formal_state_map_complete'] is False and r['gate_restore_authorized'] is False
            for _, r in audit_pair(args.audit_pair, proof_run)), 'local audit authorized gate restore')
memory_report = read(HERE / 'memory-proof-reaudit.json')
memory = audit_memory(ARCHITECTURE, memory_report['proof_run'])
require(memory['shape_proofs'] == 17 and memory['memory_instances'] == 201 and
        memory['memory_bits'] == 102985156 and memory['memory_words'] == 13501966,
        'complete prior memory theorem invalid')
memory_selection = read(CHECKS / 'memory-audit/selection.json')
memory_audit = read(memory_selection['summary'])
require(memory_audit['status'] == 'passed' and memory_audit['actual_artifact_mutations_rejected'] == 178 and
        memory_audit['original_proofs_unchanged'], 'complete memory evidence mutation audit missing')
synthesis_selection = read(CHECKS / 'synthesis-model-audit/selection.json')
synthesis = read(synthesis_selection['audit'])
require(synthesis['audit'] == 'passed' and synthesis['run'] == str(PRODUCTION) and
        synthesis['original_state_entries'] == 1543 and synthesis['original_state_bits'] == 102993417 and
        synthesis['physical_bits'] == 102992412 and synthesis['physical_register_bits'] == 7256 and
        synthesis['physical_memory_instances'] == 201 and synthesis['retiming'] is False and
        synthesis['formal_state_map_complete'] is False and synthesis['gate_restore_authorized'] is False,
        'complete synthesis/model-binding reaudit missing')
for name in ('models.v', 'cell-adapter.json', 'gate-storage-inventory.json',
             'netlist-design.v', 'model-binding.json'):
    require(file_sha(Path(synthesis_selection['evidence']) / name) == file_sha(EVIDENCE / name),
            'fresh synthesized hierarchy/model binding differs: ' + name)
wave_selection = read(CHECKS / 'waveform-audit/selection.json')
wave = read(wave_selection['summary'])
require(wave['status'] == 'pass' and len(wave['cases']) == 2 and not wave['formal_state_map_complete'] and
        not wave['gate_restore_authorized'], 'full previous production waveform audit incomplete')
for case in wave['cases']:
    require(case['zero_edge_waveform_state_words'] == 13503308 and case['checked_boundaries'] == 250185 and
            case['checked_input_output_values'] == 12008880 and case['actual_edges'] == 250185 and
            case['declarations']['complete_memories'] == 201 and case['declarations']['boundary_ports'] == 50,
            'reduced production waveform scope')
m2 = read(CHECKS / 'semantic-regression-retry/summary.json')
m3 = read(CHECKS / 'banked-regression/summary.json')
require(len(m2['cases']) == 5 and m2['words'] == 22 and m2['first_mismatch']['cycle'] == 29 and
        len(m2['restore_rejections']) == 4, 'M2 regression scope incomplete')
require(m3['transport_edges'] == 717 and m3['target_semantic_advances'] == 23 and len(m3['captures']) == 6 and
        m3['clean_replay_samples'] == 242 and m3['semantic_replay_samples'] == 5 and
        m3['invalid_client_reads_rejected'] == 8, 'M3 regression scope incomplete')
current_tests = unittest.defaultTestLoader.discover(str(ROOT / 'tools/checkpoint_formats/tests'),
                                                   pattern='test_*.py').countTestCases()
test_log = (args.python_test_log or CHECKS / 'python-tests-final.log').resolve()
require(args.python_tests == current_tests and current_tests >= 151 and
        re.search(r'Ran ' + str(current_tests) + r' tests in .*\n\nOK\s*$',
                  test_log.read_text()),
        'complete Python tests not run')
protected = read(CHECKS / 'protected-inputs.json')
require(all(file_sha(p) == h for p, h in protected.items()), 'read-only protected inputs changed')
require(subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT) ==
        (CHECKS / 'initial-staging.txt').read_bytes(), 'staging changed')
require(subprocess.check_output(['git', '-C', str(ROOT / 'sims/firesim'), 'status', '--short']) ==
        (CHECKS / 'initial-firesim-status.txt').read_bytes(), 'FireSim worktree changed')
whitespace = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
require(whitespace.returncode == 0, whitespace.stdout + whitespace.stderr)
summary = dict(milestone='M10-production-dut-formal-map', iteration=args.iteration, status='in_progress',
               production_run=str(PRODUCTION), configuration='AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config',
               final_queue_proof=str(proof), local_proof_scope=positive['proof_scope'],
               retained_modules=165, local_register_bits=1135, register_induction_assertions=1135,
               memory_port_congruence_assertions=660, output_assertions_proven=917, output_assertions_unproven=304,
               assertions_proven=2712, covers=6276, prior_negative_proofs_reaudited=8,
               independent_audit_summaries=audits, audit_passes=2, artifact_mutations_rejected_per_pass=24,
               audit_pair=str(args.audit_pair.resolve()),
               incomplete_map_loader_rejections={'binding': 'invalid ASIC state map',
                                                'audited_local_proof': 'incomplete formal build artifacts'},
               complete_semantic_entries=1543, semantic_register_bits=8261, physical_register_bits=7256,
               remaining_semantic_register_bits_without_local_proof=7126,
               remaining_physical_register_bits_without_local_proof=6121, register_count_difference=1005,
               complete_physical_storage_shapes=7457, physical_bits=102992412,
               all_global_physical_relationships='unproven until complete hierarchy composition',
               complete_synthesis_and_concrete_model_binding_reaudited=True, retiming=False,
               prior_memory_theorems_reaudited=17, prior_memory_artifact_mutations_rejected=178,
               prior_full_production_RTL_waveforms_reaudited=True, zero_edge_words_per_process=13503308,
               RTL_boundaries_per_process=250185, RTL_input_output_values_per_process=12008880,
               python_tests=args.python_tests, M2_full_regression='passed', M3_full_regression='passed',
               formal_state_map_complete=False, gate_state_load=False, gate_replay=False,
               mapped_state_corruption='not run: full production mapping remains unproven',
               external_dependency_missing=None, physical_FPGA_validated=False, power_analysis=False,
               protected_inputs_and_staging_preserved=True,
               next='Discharge 304 local output counterexamples with full-DUT hierarchy/invariant proofs; complete top register, optimized-state, all memory and boundary composition before map/gate restore/replay')
(OUT / 'summary.json').write_bytes(canonical(summary))
(OUT / 'protected-and-whitespace-audit.json').write_bytes(canonical(dict(
    protected_inputs_unchanged=True, staging_unchanged=True, firesim_worktree_unchanged=True, whitespace='passed')))
(OUT / 'proof-selection.json').write_bytes(canonical(dict(
    run=str(proof_run), proof=str(proof), summary=str(proof_run / 'summary.json'),
    audit_pair=str(args.audit_pair.resolve()), audit_pair_sha256=file_sha(args.audit_pair))))
source_files = [ROOT / p for p in (
    'tools/checkpoint_formats/evidence.py', 'tools/checkpoint_formats/tests/test_evidence.py',
    'tools/checkpoint_formats/tests/finalize_production_queue.py',
    'tools/checkpoint_formats/production_queue.py', 'tools/checkpoint_formats/tests/verify_production_queue.py',
    'tools/checkpoint_formats/tests/audit_production_queue.py', 'tools/checkpoint_formats/tests/test_production_queue.py',
    'docs/checkpointing/m10-production-dut-formal-map.md', 'docs/checkpointing/progress.md')]
# Include actual selected CAD proof bytes, all mutation evidence and replay
# artifacts, plus every newly created diagnostic file. Catalogs cannot hash
# themselves or the finalizer's still-open stdout log.
roots = (OUT, CHECKS, proof_run, ARCHITECTURE, PRODUCTION / 'synthesis', EVIDENCE,
         Path(synthesis_selection['evidence']), Path(memory_report['proof_run']),
         *(p.parent for p, _ in selected_audits))
paths = {p.absolute() for root in roots for p in root.rglob('*') if p.is_file() and
         p.name not in ('artifact-manifest.json', 'finalize-evidence.log')}
paths.update(source_files)
paths.update(Path(p) for _, report in audit_pair(args.audit_pair, proof_run)
             for p in report['original_proof_hashes'])
paths.add(args.audit_pair.resolve())
paths.add(test_log)
paths.add(HERE / 'memory-proof-reaudit.json')
empty = [dict(path=str(p.resolve()), bytes=0, sha256=file_sha(p)) for p in sorted(paths)
         if p.stat().st_size == 0]
catalog = artifact_catalog([p for p in paths if p.stat().st_size > 0]) + empty
(OUT / 'artifact-manifest.json').write_bytes(canonical(sorted(catalog, key=lambda r: r['path'])))
print(json.dumps(summary, indent=2))
