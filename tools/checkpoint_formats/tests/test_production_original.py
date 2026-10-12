from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_dut import extract_architecture
from tools.checkpoint_formats.production_original import miter, original_cut, proof_inputs, properties, validate, validate_domains
from tools.checkpoint_formats.tests.test_production_dut import RTL, inputs
from tools.checkpoint_formats.tests.audit_production_original import audit_original_cut
from tools.checkpoint_formats.tests.verify_production_original import negative_binding


def example():
    candidate, original, architecture, models, _ = extract_architecture(*inputs(), RTL)
    entries = candidate['entries']
    return dict(top=candidate['top'], reference_source=original, implementation_source=architecture,
                standard_models='', memory_source=models,
                memories=[dict(entry=e, gate_components=e['architecture_path'].split('.')[:-1])
                          for e in entries if e['kind'] == 'memory'],
                registers=[e for e in entries if e['kind'] == 'register'], register_bits=4, memory_bits=32)


class ProductionOriginalTests(unittest.TestCase):
    def test_actual_original_cut_keeps_pipeline_and_exact_port_expressions(self):
        binding = example()
        source, _, _, exposure = original_cut(binding)
        self.assertIn('pipeline <= rd;', source)
        self.assertNotIn('mem[wa]', source)
        self.assertNotIn('mem[ra]', source)
        self.assertIn('assign ckregister_memory_0_WE = enable;', source)
        self.assertIn('assign rd2 = ckregister_memory_0_Q1;', source)
        self.assertEqual(len(exposure), 8)
        self.assertNotIn('CKMEM_', source)

    def test_missing_array_hidden_access_and_wrong_module_reject(self):
        for fault in ('missing', 'hidden', 'module'):
            binding = example()
            if fault == 'missing': binding['memories'].clear()
            elif fault == 'hidden': binding['reference_source'] = binding['reference_source'].replace('assign q = pipeline;', 'assign q = mem[wa];')
            else: binding['memories'][0]['entry']['module'] = 'Unknown'
            with self.subTest(fault=fault), self.assertRaises(FormatError):
                original_cut(binding)

    def test_full_register_relation_and_independent_read_closure(self):
        binding = example()
        for kind in ('address', 'word'):
            text = miter(binding, kind).decode()
            self.assertIn('(reference.pipeline == implementation.pipeline)', text)
            self.assertNotIn('assume property', text)
            self.assertNotIn('reset -', text)
            self.assertIn('port_ckregister_memory_0_RA1: assert property', text)
        address = miter(binding, 'address').decode()
        self.assertIn('input [3:0] reference_ckregister_memory_0_Q0', address)
        self.assertIn('input [3:0] implementation_ckregister_memory_0_Q0', address)
        self.assertNotIn('register_0_step:', address)
        word = miter(binding, 'word').decode()
        self.assertIn('register_0_step: assert property', word)
        self.assertIn('register_0_bit_3_1: cover property', word)
        self.assertIn('input [2:0] watched_0', word)
        self.assertIn('word_0_step: assert property', word)
        self.assertIn('port_ckregister_memory_0_WD: assert property', word)

    def test_extra_storage_edges_and_gated_architecture_clock_reject(self):
        for fault in ('negedge', 'gated', 'implicit_event'):
            binding = example()
            validate_domains(binding)
            if fault == 'negedge':
                binding['reference_source'] = binding['reference_source'].replace('posedge clock', 'negedge clock')
            elif fault == 'gated':
                binding['implementation_source'] = binding['implementation_source'].replace('.CP(clock)', '.CP(clock & we)')
            else:
                binding['reference_source'] = binding['reference_source'].replace('always @(posedge clock)', 'always @*')
            with self.subTest(fault=fault), self.assertRaises(FormatError):
                validate_domains(binding)

    def test_independent_cut_audit_rejects_dropped_pipeline_and_changed_write_witness(self):
        binding = example()
        text = miter(binding, 'word').decode()
        audit_original_cut(binding, text)
        for changed in (text.replace('pipeline <= rd;', 'pipeline <= 0;', 1),
                        text.replace('ckregister_memory_0_WE = enable;', 'ckregister_memory_0_WE = we;', 1),
                        text.replace('reg [3:0] pipeline;', 'reg [3:0] pipeline; reg hidden;', 1)):
            with self.subTest(changed=changed), self.assertRaises(FormatError):
                audit_original_cut(binding, changed)

    def test_unproven_missing_and_vacuous_native_obligations_reject(self):
        binding = example()
        for kind in ('address', 'word'):
            artifacts = proof_inputs(binding, kind)
            expected = properties(binding, kind)
            assertion = next(p for p, k in expected.items() if k == 'assert')
            for fault in ('missing', 'cex', 'undetermined', 'vacuous'):
                with tempfile.TemporaryDirectory() as directory:
                    proof = Path(directory)
                    for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
                        (proof / name).write_bytes(artifacts[role])
                    statuses = {p: (k, 'proven' if k == 'assert' else 'covered') for p, k in expected.items()}
                    if fault == 'missing': statuses.pop(assertion)
                    elif fault == 'vacuous': statuses[assertion + ':precondition1'] = ('cover', 'unreachable')
                    else: statuses[assertion] = ('assert', fault)
                    rows = ['FORMAT\tproduction-original-v1'] + ['INPUT\t' + r + '\t' + sha(a) for r, a in artifacts.items()]
                    rows += ['PROPERTY\t' + p + '\t' + '\t'.join(s) for p, s in statuses.items()]
                    (proof / 'original-results.tsv').write_text('\n'.join(rows + ['END', '']))
                    with self.subTest(kind=kind, fault=fault), self.assertRaises(FormatError):
                        validate(binding, kind, proof)

    def test_component_certificate_cannot_authorize_gate_load(self):
        with self.assertRaises(FormatError):
            gate_deposits(dict(artifact_type='production_original_architecture_composition',
                               formal_state_map_complete=False, gate_restore_authorized=False), {}, {}, {}, b'', {}, 'tb.dut')

    def test_actual_port_faults_remain_in_the_supported_named_port_grammar(self):
        binding = example()
        binding['top'] = 'Queue'
        for side in ('reference', 'implementation'):
            binding[side + '_source'] = binding[side + '_source'].replace('module Pipeline(', 'module Queue(')
        for entry in binding['registers'] + [m['entry'] for m in binding['memories']]:
            entry['module'] = 'Queue'
        for fault in ('address_port', 'address_feedback', 'word_data', 'word_enable'):
            value, kind, prop = negative_binding(binding, fault)
            with self.subTest(fault=fault):
                text = proof_inputs(value, kind)['miter'].decode()
                self.assertIn(prop.split('::', 1)[1].split('.', 1)[1] + ': assert property', text)
                self.assertNotEqual(value['implementation_source'], binding['implementation_source'])


if __name__ == '__main__':
    unittest.main()
