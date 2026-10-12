from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_memory_composition import address_miter, clock_tree, proof_inputs, properties, validate, validate_read_domains, word_miter
from tools.checkpoint_formats.tests.test_production_register import example as register_example


def example():
    registers = register_example()
    return dict(registers=registers, instances=[dict(index=0, width=1, depth=2, read_ports=1)],
                memory_instances=1, memory_bits=2, memory_words=2, read_ports=1)


class ProductionMemoryCompositionTests(unittest.TestCase):
    def test_single_word_reads_require_zero_on_both_actual_hierarchies(self):
        binding = example()['registers']
        binding['memories'][0]['entry']['depth'] = 1
        for side in ('reference', 'implementation'):
            binding[side + '_source'] = binding[side + '_source'].replace('.RA0(address)', ".RA0(1'b0)")
        validate_read_domains(binding)
        for side in ('reference', 'implementation'):
            original = binding[side + '_source']
            for bad in ("1'b1", 'address'):
                binding[side + '_source'] = original.replace(".RA0(1'b0)", '.RA0(' + bad + ')')
                with self.subTest(side=side, bad=bad), self.assertRaisesRegex(FormatError, 'single-word read address'):
                    validate_read_domains(binding)
            binding[side + '_source'] = original

    def test_gated_clock_rejects_even_if_its_sampled_value_could_agree(self):
        binding = example()['registers']
        self.assertTrue(clock_tree(binding)['implementation'])
        binding['implementation_source'] = binding['implementation_source'].replace('.CP(clock)', '.CP(clock & reset)', 1)
        with self.assertRaisesRegex(FormatError, 'gated storage clock'):
            clock_tree(binding)

    def test_read_closure_requires_independently_quantified_words(self):
        binding = example()
        text = address_miter(binding).decode()
        for side in ('reference', 'implementation'):
            self.assertIn('input [0:0] ' + side + '_ckregister_memory_0_Q0', text)
            self.assertIn('.ckregister_memory_0_Q0(' + side + '_ckregister_memory_0_Q0)', text)
            self.assertIn(side + '_ckregister_memory_0_CP_target_clock: assert property', text)
        self.assertIn('ckregister_memory_0_RA0_equal: assert property', text)
        self.assertIn('reference_ckregister_memory_0_Q0 != implementation_ckregister_memory_0_Q0', text)
        self.assertNotIn('assume property', text)
        self.assertNotIn('word_0_step:', text)

    def test_word_projection_keeps_existing_register_and_port_obligations(self):
        binding = example()
        text = word_miter(binding).decode()
        self.assertIn('state_0_step: assert property', text)
        self.assertIn('port_ckregister_memory_0_WD: assert property', text)
        self.assertIn('pending_0_bit_1_1: cover property', text)
        self.assertIn('input [0:0] watched_0', text)
        self.assertIn('old_reference_0 == old_implementation_0', text)
        self.assertIn('implementation_ckregister_memory_0_WA == watched_0', text)
        self.assertIn('word_0_step: assert property', text)
        self.assertNotIn('assume property', text)

    def test_missing_word_address_or_nonvacuity_rejects_without_native_log(self):
        binding = example()
        for kind in ('address', 'word'):
            artifacts = proof_inputs(binding, kind)
            expected = properties(binding, kind)
            assertion = next(p for p in expected if p.endswith('_equal')) if kind == 'address' else next(
                p for p in expected if p.endswith('.word_0_step'))
            for fault in ('missing', 'cex', 'undetermined', 'vacuous'):
                with tempfile.TemporaryDirectory() as directory:
                    proof = Path(directory)
                    for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
                        (proof / name).write_bytes(artifacts[role])
                    statuses = {p: (k, 'proven' if k == 'assert' else 'covered') for p, k in expected.items()}
                    if fault == 'missing': statuses.pop(assertion)
                    elif fault == 'vacuous': statuses[assertion + ':precondition1'] = ('cover', 'unreachable')
                    else: statuses[assertion] = ('assert', fault)
                    rows = ['FORMAT\tproduction-composition-v1']
                    rows += ['INPUT\t' + r + '\t' + sha(a) for r, a in artifacts.items()]
                    rows += ['PROPERTY\t' + p + '\t' + '\t'.join(s) for p, s in statuses.items()]
                    (proof / 'composition-results.tsv').write_text('\n'.join(rows + ['END', '']))
                    with self.subTest(kind=kind, fault=fault), self.assertRaises(FormatError):
                        validate(binding, kind, proof)

    def test_modified_shared_read_word_miter_rejects_before_results(self):
        binding = example()
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory)
            artifacts = proof_inputs(binding, 'address')
            for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
                (proof / name).write_bytes(artifacts[role])
            text = (proof / 'miter.sv').read_text().replace('implementation_ckregister_memory_0_Q0', 'reference_ckregister_memory_0_Q0')
            (proof / 'miter.sv').write_text(text)
            with self.assertRaisesRegex(FormatError, 'unbound memory composition inputs'):
                validate(binding, 'address', proof)

    def test_conditional_memory_proof_never_authorizes_loading(self):
        with self.assertRaises(FormatError):
            gate_deposits(dict(artifact_type='conditional_production_memory_composition',
                               formal_state_map_complete=False, gate_restore_authorized=False), {}, {}, {}, b'', {}, 'tb.dut')


if __name__ == '__main__':
    unittest.main()
