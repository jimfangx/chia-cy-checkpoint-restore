import copy
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import gate_deposits
from tools.checkpoint_formats.production_state_map import compose_entries


def example():
    register = dict(state_id='register', original_path='pipe.saved', architecture_path='pipe.saved',
                    kind='register', width=3, depth=1)
    array = dict(state_id='memory', original_path='ram', architecture_path='ckmem.contents',
                 kind='memory', width=5, depth=8, memory=dict(cell='CKMEM'))
    original = dict(registers=[register], memories=[dict(entry=array)], register_bits=3)
    memory = dict(registers=dict(groups=[dict(entry=register, bits=[dict(original_bit=0, gate_components=['pipe', 'saved_reg'], xor=0)])]),
                  instances=[dict(index=0, state_id='memory', original_path='ram', architecture_path='ckmem.contents',
                                  cell='CKMEM', width=5, depth=8, gate_components=['ckmem'], read_ports=1,
                                  universal_original_adapter='/adapter', original_adapter_properties=['word_step', 'read_0'])])
    optimized = dict(classifications=[dict(state_id='register', original_path='pipe.saved', width=3, bit=1,
                                          classification='conditional_constant', value=0, value_covers=['zero', 'one'],
                                          preservation_property='predicate_step'),
                                     dict(state_id='register', original_path='pipe.saved', width=3, bit=2,
                                          classification='conditional_irrelevant', value_covers=['zero', 'one'])])
    inventory = dict(storage=[dict(instance_components=['pipe', 'saved_reg'], name='state', cell='CKDFF',
                                   kind='register', width=1, depth=1),
                              dict(instance_components=['ckmem'], name='contents', cell='CKMEM', kind='memory', width=5, depth=8)],
                     physical_bits=41, physical_words=9)
    return original, memory, optimized, inventory


class ProductionStateMapTests(unittest.TestCase):
    def test_complete_array_and_pipeline_state_are_accounted(self):
        entries = compose_entries(*example())
        mem, reg = entries
        self.assertEqual(mem['mapping']['address_count'], 8)
        self.assertEqual(mem['mapping']['bit_count'], 5)
        self.assertEqual([b['classification'] for b in reg['bits']], ['mapped', 'preserved_predicate', 'irrelevant'])
        self.assertNotIn('gate', reg['bits'][1])
        self.assertNotIn('value', reg['bits'][2])

    def test_missing_bit_never_becomes_irrelevant_implicitly(self):
        args = example()
        args[2]['classifications'].pop()
        with self.assertRaisesRegex(FormatError, 'missing semantic register bit'):
            compose_entries(*args)

    def test_hidden_physical_state_rejects(self):
        args = example()
        args[3]['storage'].append(dict(instance_components=['extra'], name='state', cell='CKDFF', kind='register', width=1, depth=1))
        with self.assertRaisesRegex(FormatError, 'unmapped physical storage'):
            compose_entries(*args)

    def test_all_register_relationships_require_exact_shapes_and_polarity(self):
        for fault in ('shape', 'path', 'polarity', 'boolean', 'bit', 'duplicate'):
            args = example()
            bit = args[1]['registers']['groups'][0]['bits'][0]
            if fault == 'shape': args[3]['storage'][0]['width'] = 2
            elif fault == 'path': bit['gate_components'] = ['missing']
            elif fault == 'polarity': bit['xor'] = 1
            elif fault == 'boolean': bit['xor'] = False
            elif fault == 'bit': bit['original_bit'] = 3
            else: args[1]['registers']['groups'][0]['bits'].append(copy.deepcopy(bit))
            with self.subTest(fault=fault), self.assertRaises(FormatError):
                compose_entries(*args)

    def test_predicate_and_irrelevance_cannot_overlap_mapped_state(self):
        for fault in ('overlap', 'duplicate', 'unknown', 'width', 'path', 'classification', 'value'):
            args = example()
            item = args[2]['classifications'][0]
            if fault == 'overlap': item['bit'] = 0
            elif fault == 'duplicate': args[2]['classifications'].append(copy.deepcopy(item))
            elif fault == 'unknown': item['state_id'] = 'missing'
            elif fault == 'width': item['width'] = 4
            elif fault == 'path': item['original_path'] = 'wrong'
            elif fault == 'classification': item['classification'] = 'unproven'
            else: item['value'] = 2
            with self.subTest(fault=fault), self.assertRaises(FormatError):
                compose_entries(*args)

    def test_every_memory_word_and_port_model_must_be_bound(self):
        for fault in ('missing', 'duplicate', 'state_id', 'width', 'depth', 'path', 'cell', 'storage'):
            args = example()
            item = args[1]['instances'][0]
            if fault == 'missing': args[1]['instances'].clear()
            elif fault == 'duplicate': args[1]['instances'].append(copy.deepcopy(item))
            elif fault == 'state_id': item['state_id'] = 'missing'
            elif fault == 'width': item['width'] = 4
            elif fault == 'depth': item['depth'] = 7
            elif fault == 'path': item['gate_components'] = ['missing']
            elif fault == 'cell': item['cell'] = 'opaque'
            else: args[3]['storage'][1]['name'] = 'read_data'
            with self.subTest(fault=fault), self.assertRaises(FormatError):
                compose_entries(*args)

    def test_physical_count_and_duplicate_inventory_cannot_pass(self):
        for fault in ('bits', 'words', 'duplicate'):
            args = example()
            if fault == 'bits': args[3]['physical_bits'] -= 1
            elif fault == 'words': args[3]['physical_words'] -= 1
            else: args[3]['storage'].append(copy.deepcopy(args[3]['storage'][0]))
            with self.subTest(fault=fault), self.assertRaises(FormatError):
                compose_entries(*args)

    def test_complete_production_map_requires_its_own_loader(self):
        with self.assertRaisesRegex(FormatError, 'production loader'):
            gate_deposits(dict(top='ActualDUT', production_state_map_version=1, formal_state_map_complete=True,
                               gate_restore_authorized=False), {}, {}, {}, b'', {}, 'tb.dut')


if __name__ == '__main__':
    unittest.main()
