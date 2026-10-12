import copy
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import gate_deposits
from tools.checkpoint_formats.production_optimized import PREFIX, partition


def example():
    entry = dict(state_id='reg', original_path='saved', width=3, depth=1, kind='register')
    binding = dict(groups=[dict(entry=entry, bits=[dict(original_bit=0)])],
                   pending_registers=[dict(entry=entry, bits=[1, 2])],
                   optimized_predicates=[dict(entry=entry, bit=1, value=0)],
                   physical_register_bits=1, semantic_register_bits=3)
    results = {PREFIX + 'predicate_0_step': ('assert', 'proven'),
               PREFIX + 'predicate_0_holds': ('cover', 'covered')}
    for bit in (1, 2):
        for value in (0, 1):
            results[PREFIX + f'pending_0_bit_{bit}_{value}'] = (
                'cover', 'unreachable' if bit == 1 and value == 1 else 'covered')
    return binding, results


class ProductionOptimizedTests(unittest.TestCase):
    def test_conditional_certificate_cannot_initialize_gate_state(self):
        certificate = dict(artifact_type='conditional_production_optimized_relations',
                           formal_state_map_complete=False, gate_restore_authorized=False)
        with self.assertRaises(FormatError):
            gate_deposits(certificate, {}, {}, {}, b'', {}, 'tb.dut')

    def test_preserved_constant_and_unconstrained_bit_are_distinct(self):
        binding, results = example()
        constant, free = partition(binding, results)
        self.assertEqual(constant['classification'], 'conditional_constant')
        self.assertEqual(constant['value'], 0)
        self.assertEqual(free['classification'], 'conditional_irrelevant')
        self.assertNotIn('value', free)
        self.assertNotIn('preservation_property', free)
        self.assertTrue(all(c['global_state_map_status'].startswith('unproven') for c in (constant, free)))

    def test_unreachable_free_value_does_not_establish_constant(self):
        binding, results = example()
        results[PREFIX + 'pending_0_bit_2_1'] = ('cover', 'unreachable')
        with self.assertRaisesRegex(FormatError, 'independence nonvacuity'):
            partition(binding, results)

    def test_missing_predicate_must_not_become_irrelevant(self):
        binding, results = example()
        binding['optimized_predicates'].clear()
        with self.assertRaisesRegex(FormatError, 'independence nonvacuity'):
            partition(binding, results)

    def test_failed_or_vacuous_predicate_rejects(self):
        for prop, status in (('step', ('assert', 'cex')), ('step', ('assert', 'undetermined')),
                             ('holds', ('cover', 'unreachable'))):
            binding, results = example()
            results[PREFIX + 'predicate_0_' + prop] = status
            with self.subTest(prop=prop, status=status), self.assertRaisesRegex(FormatError, 'unproven/vacuous'):
                partition(binding, results)

    def test_missing_or_wrong_kind_free_covers_reject(self):
        for status in (None, ('assert', 'proven'), ('cover', 'undetermined')):
            binding, results = example()
            key = PREFIX + 'pending_0_bit_2_0'
            if status is None: results.pop(key)
            else: results[key] = status
            with self.subTest(status=status), self.assertRaises(FormatError):
                partition(binding, results)

    def test_incomplete_duplicate_and_overlap_partitions_reject(self):
        for kind in ('missing', 'duplicate', 'overlap', 'out_of_range', 'retained_duplicate'):
            binding, results = example()
            bits = binding['pending_registers'][0]['bits']
            if kind == 'missing': bits.pop()
            elif kind == 'duplicate': bits.append(2)
            elif kind == 'overlap': bits.append(0)
            elif kind == 'out_of_range': bits.append(3)
            else: binding['groups'][0]['bits'].append(dict(original_bit=0))
            with self.subTest(kind=kind), self.assertRaises(FormatError):
                partition(binding, results)

    def test_predicate_must_bind_exact_omitted_entry_and_binary_value(self):
        for kind in ('retained', 'shape', 'duplicate', 'value', 'boolean'):
            binding, results = example()
            predicate = binding['optimized_predicates'][0]
            if kind == 'retained': predicate['bit'] = 0
            elif kind == 'shape': predicate['entry'] = dict(predicate['entry'], width=4)
            elif kind == 'duplicate': binding['optimized_predicates'].append(copy.deepcopy(predicate))
            elif kind == 'value': predicate['value'] = 2
            else: predicate['value'] = False
            with self.subTest(kind=kind), self.assertRaisesRegex(FormatError, 'unbound/duplicate/unsupported'):
                partition(binding, results)

    def test_opposite_predicate_value_needs_consistent_native_covers(self):
        binding, results = example()
        binding['optimized_predicates'][0]['value'] = 1
        with self.assertRaisesRegex(FormatError, 'conditional constant covers'):
            partition(binding, results)
        results[PREFIX + 'pending_0_bit_1_0'] = ('cover', 'unreachable')
        results[PREFIX + 'pending_0_bit_1_1'] = ('cover', 'covered')
        self.assertEqual(partition(binding, results)[0]['value'], 1)


if __name__ == '__main__':
    unittest.main()
