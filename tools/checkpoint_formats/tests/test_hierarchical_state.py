import copy
from pathlib import Path
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.hierarchical_state import architecture_cell_adapter, bind_concrete_models, hierarchical_inventory
from tools.checkpoint_formats.production_dut import extract_architecture
from tools.checkpoint_formats.tests.test_production_dut import RTL, inputs


class HierarchicalStorageTests(unittest.TestCase):
    def setUp(self):
        candidate, _, _, memories, _ = extract_architecture(*inputs(), RTL)
        fixture = Path(__file__).with_name('fixtures') / 'formal'
        import json
        self.models, self.adapter = architecture_cell_adapter(candidate, json.loads((fixture / 'cell-adapter.json').read_text()),
                                                             (fixture / 'cells.v').read_text(), memories)
        self.netlist = '''module Wrapper(clock, q);
input clock; output q; wire d;
CKDFF \\bit_reg[0] (.CP(clock), .D(d), .Q(q));
assign d = ~q;
endmodule
module DUT(clock, q, q2);
input clock; output q, q2;
Wrapper a(.clock(clock), .q(q));
Wrapper b(.clock(clock), .q(q2));
CKMEM_W4_D8_R2 memory(.CP(clock), .WE(1'b0), .WA(3'b0), .WD(4'b0),
.RA0(3'b0), .Q0(), .RA1(3'b0), .Q1());
endmodule'''

    def test_each_hierarchy_copy_and_all_memory_words_count(self):
        inventory = hierarchical_inventory(self.netlist, self.models, self.adapter, 'DUT')
        self.assertEqual(inventory['physical_bits'], 34)
        self.assertEqual(inventory['physical_words'], 10)
        self.assertEqual([r['instance_components'] for r in inventory['storage']],
                         [['a', 'bit_reg[0]'], ['b', 'bit_reg[0]'], ['memory']])
        self.assertEqual(inventory['proof_status'], 'unproven')

    def test_large_memory_remains_a_complete_span(self):
        models = self.models.replace('CKMEM_W4_D8_R2', 'CKMEM_W4_D524288_R2').replace('[0:7]', '[0:524287]')
        adapter = copy.deepcopy(self.adapter)
        from tools.checkpoint_formats.formal_state_map import sha
        adapter['models_sha256'] = sha(models.encode())
        spec = adapter['cells'].pop('CKMEM_W4_D8_R2')
        spec['storage'][0]['depth'] = 524288
        adapter['cells']['CKMEM_W4_D524288_R2'] = spec
        inventory = hierarchical_inventory(self.netlist.replace('CKMEM_W4_D8_R2', 'CKMEM_W4_D524288_R2'), models, adapter, 'DUT')
        self.assertEqual(inventory['physical_bits'], 2097154)
        self.assertEqual(len(inventory['storage']), 3)

    def test_unknown_cell_stub_procedural_state_and_bad_clock_reject(self):
        for netlist in (self.netlist.replace('Wrapper a', 'UNKNOWN a'),
                        self.netlist + '\nmodule CKDFF(input CP, input D, output Q); endmodule',
                        self.netlist.replace('wire d;', 'wire d; reg hidden;'),
                        self.netlist.replace('.CP(clock)', '.CP(q)'),
                        self.netlist.replace('.clock(clock)', '.clock(q)'),
                        self.netlist.replace('.WE(1\'b0), ', ''),
                        self.netlist.replace('Wrapper a', 'DUT a')):
            with self.subTest(netlist=netlist), self.assertRaises(FormatError):
                hierarchical_inventory(netlist, self.models, self.adapter, 'DUT')

    def test_hidden_model_pipeline_or_incomplete_memory_span_rejects(self):
        from tools.checkpoint_formats.formal_state_map import sha
        for mutation in ('reg hidden;', 'initial contents[0]=0;', 'logic hidden;'):
            models = self.models.replace('endmodule', mutation + '\nendmodule', 1)
            adapter = dict(self.adapter, models_sha256=sha(models.encode()))
            with self.subTest(mutation=mutation), self.assertRaises(FormatError):
                hierarchical_inventory(self.netlist, models, adapter, 'DUT')
        adapter = copy.deepcopy(self.adapter)
        adapter['cells']['CKMEM_W4_D8_R2']['storage'][0]['depth'] = 7
        with self.assertRaises(FormatError):
            hierarchical_inventory(self.netlist, self.models, adapter, 'DUT')

    def test_emitted_memory_interface_requires_the_exact_concrete_model(self):
        stub = '''module CKMEM_W4_D8_R2(CP, WE, WA, WD, RA0, RA1, Q0, Q1);
input CP, WE; input [2:0] WA, RA0, RA1; input [3:0] WD;
output [3:0] Q0, Q1; wire CP, WE; endmodule'''
        inventory = hierarchical_inventory(self.netlist + '\n' + stub, self.models, self.adapter, 'DUT')
        self.assertEqual(inventory['physical_bits'], 34)
        self.assertIn('CKMEM_W4_D8_R2', inventory['emitted_memory_interfaces'])
        import json
        self.assertEqual(json.loads(json.dumps(inventory)), inventory)
        for mutation in (stub.replace('output [3:0]', 'output [2:0]'),
                         stub.replace('wire CP, WE;', 'reg hidden;'),
                         stub.replace('wire CP, WE;', "assign Q0 = 4'b0;")):
            with self.subTest(stub=mutation), self.assertRaises(FormatError):
                hierarchical_inventory(self.netlist + '\n' + mutation, self.models, self.adapter, 'DUT')
        selected, binding = bind_concrete_models(self.netlist + '\n' + stub, self.models, self.adapter, 'DUT')
        self.assertEqual(selected.strip(), self.netlist.strip())
        self.assertEqual(binding['removed_declaration_only_memory_interfaces'], ['CKMEM_W4_D8_R2'])
        self.assertFalse(binding['gate_restore_authorized'])


if __name__ == '__main__':
    unittest.main()
