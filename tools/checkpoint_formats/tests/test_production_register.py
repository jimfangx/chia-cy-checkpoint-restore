import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.production_register import cut_design, miter, proof_inputs, validate


def example():
    entry = dict(state_id='reg', original_path='saved', width=1, depth=1, kind='register')
    mem = dict(state_id='mem', architecture_path='ckmem_ram.contents', width=1, depth=2,
               memory=dict(cell='CKMEM_W1_D2_R1'))
    reference = '''module DUT(input clock, input reset, input address, input data, output result);
reg saved;
wire word;
assign result = saved ^ word;
always @(posedge clock) saved <= data;
CKMEM_W1_D2_R1 ckmem_ram(.CP(clock), .WE(reset), .WA(address), .WD(data), .RA0(address), .Q0(word));
endmodule
'''
    implementation = '''module DUT(clock, reset, address, data, result);
input clock, reset, address, data;
output result;
wire saved, word;
assign result = saved ^ word;
CKDFF saved_reg(.CP(clock), .D(data), .Q(saved));
CKMEM_W1_D2_R1 ckmem_ram(.CP(clock), .WE(reset), .WA(address), .WD(data), .RA0(address), .Q0(word));
endmodule
'''
    return dict(top='DUT', reference_source=reference, implementation_source=implementation,
                standard_models='module CKDFF(input CP, input D, output Q);\nreg state;\nalways @(posedge CP) state <= D;\nassign Q = state;\nendmodule\n',
                memory_source='module CKMEM_W1_D2_R1(input CP, input WE, input WA, input WD, input RA0, output Q0);\nendmodule\n',
                memories=[dict(entry=mem, gate_components=['ckmem_ram'])],
                groups=[dict(entry=entry, bits=[dict(original_bit=0, gate_components=['saved_reg'], xor=0)])],
                pending_registers=[dict(entry=dict(entry, original_path='unused', width=2), bits=[0, 1])])


class ProductionRegisterTests(unittest.TestCase):
    def test_predicate_requires_preservation_and_retains_pending_state(self):
        binding = example()
        binding['optimized_predicates'] = [dict(entry=dict(original_path='unused', width=2), bit=1, value=0)]
        text = miter(binding).decode()
        self.assertIn("(reference.unused[1] == 1'b0)", text)
        self.assertIn('predicate_0_step: assert property', text)
        self.assertIn('predicate_0_holds: cover property', text)
        self.assertIn('pending_0_bit_1_1: cover property', text)
        self.assertNotIn('assume property', text)

    def test_complete_array_cut_preserves_actual_storage_and_every_port(self):
        binding = example()
        source, name, interface, exposure = cut_design(binding, 'reference')
        self.assertIn('reg saved;', source)
        self.assertIn('saved <= data;', source)
        self.assertNotIn('CKMEM_W1_D2_R1 ckmem_ram', source)
        self.assertEqual(set(exposure), {'ckregister_memory_0_' + p for p in ('CP', 'WE', 'WA', 'WD', 'RA0', 'Q0')})
        text = miter(binding).decode()
        for p in ('CP', 'WE', 'WA', 'WD', 'RA0'):
            self.assertIn('port_ckregister_memory_0_' + p + ': assert property', text)
        self.assertIn('port_result: assert property', text)
        self.assertIn('state_0_step: assert property', text)
        self.assertIn('implementation.saved_reg.state', text)
        for bit in (0, 1):
            for value in (0, 1):
                self.assertIn(f'pending_0_bit_{bit}_{value}: cover property', text)
        self.assertNotIn('assume property', text)
        self.assertNotIn('initial ', text)

    def test_unknown_and_omitted_memories_reject(self):
        for mutation in ('path', 'missing', 'port'):
            binding = example()
            if mutation == 'path':
                binding['memories'][0]['gate_components'] = ['wrong']
            elif mutation == 'missing':
                binding['memories'].clear()
            else:
                binding['implementation_source'] = binding['implementation_source'].replace('.WE(reset), ', '')
            with self.subTest(mutation=mutation), self.assertRaises(FormatError):
                miter(binding)

    def test_missing_boundary_rejects(self):
        binding = example()
        binding['implementation_source'] = binding['implementation_source'].replace(', result)', ')').replace('output result;', '')
        with self.assertRaises(FormatError):
            miter(binding)

    def test_changed_register_relation_and_partial_evidence_reject(self):
        binding = example()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            artifacts = proof_inputs(binding)
            for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
                (path / name).write_bytes(artifacts[role])
            changed = copy.deepcopy(binding)
            changed['groups'][0]['bits'][0]['xor'] = 1
            with self.assertRaisesRegex(FormatError, 'unbound'):
                validate(changed, path)
            (path / 'register-results.tsv').write_text('FORMAT\tproduction-register-v1\nEND\n')
            with self.assertRaisesRegex(FormatError, 'identity'):
                validate(binding, path)


if __name__ == '__main__':
    unittest.main()
