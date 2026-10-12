import copy
from pathlib import Path
import re
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.production_context import (
    _parent_source, ansi_shapes, live_miter, parent_miter, proof_inputs, properties, validate, whole_miter,
)
from tools.checkpoint_formats.production_queue import instances, port_shapes
from tools.checkpoint_formats.tests.test_production_queue import example as queue_example


def example():
    header = 'input clock, input reset, input data, output ready'
    body = '''
reg saved;
wire unused;
assign ready = saved;
always @(posedge clock) begin
  if (reset) saved <= 0; else saved <= data;
end
Queue_2 q(.clock(clock), .reset(reset), .data(data), .ready(unused));
'''
    child = instances(body)['q']
    child.update(interface=port_shapes(header, body), cuts={'ready': dict(width=1, independent_mask=1)})
    spec = dict(header=header, body=body, ports=port_shapes(header, body),
                registers={'saved': 1}, children={'q': child})
    raw = '<embedded>::production_queue_miter.Queue_2_output_ready'
    return dict(parents={'Parent': spec}, queue_binding=queue_example(),
                cuts={'Queue_2': {'ready': dict(width=1, independent_mask=1, raw_obligation=raw)}},
                prior_queue_audit={'unproven_obligations': {'output': {raw: 'cex'}}})


class ProductionContextTests(unittest.TestCase):
    def test_interfaces_support_real_no_reset_and_combinational_children(self):
        self.assertEqual(ansi_shapes('input clock, output [2:0] data'),
                         {'clock': ('input', 1), 'data': ('output', 3)})
        self.assertEqual(ansi_shapes('input data, output ready'),
                         {'data': ('input', 1), 'ready': ('output', 1)})
        for header in ('input clock, input clock', 'input [1:0] clock, output data',
                       'input data, inout ready', 'input data, output reg ready'):
            with self.subTest(header=header), self.assertRaises(FormatError):
                ansi_shapes(header)
    def test_exact_cut_retains_parent_storage_and_all_child_inputs(self):
        binding = example()
        text = _parent_source('Parent', binding['parents']['Parent'], 'reference')
        self.assertIn('reg saved;', text)
        self.assertIn('saved <= data;', text)
        self.assertIn('assign unused = child_q_ready;', text)
        for p in ('clock', 'reset', 'data'):
            self.assertIn('assign child_q_' + p, text)
        self.assertNotIn('Queue_2 q', text)
        full = parent_miter(binding).decode()
        for prop in ('Parent_step_saved', 'Parent_output_ready', 'Parent_child_q_data_equal',
                     'Parent_child_q_clock_equal', 'Parent_child_q_reset_equal'):
            self.assertIn(prop + ': assert property', full)
        self.assertIn('Parent_relation |=> reference_Parent.saved', full)
        self.assertIn('different_Parent_child_q_ready', full)
        self.assertNotRegex(full, r'\b(assume|initial|restrict|force)\b')

    def test_properties_cannot_collide_with_ports(self):
        binding = example()
        text = parent_miter(binding).decode()
        labels = re.findall(r'^(\w+): (?:assert|cover)', text, re.M)
        top_ports = re.findall(r'input \[\d+:0\] (\w+)', text.split('module production_context_miter', 1)[1])
        self.assertEqual(len(labels), len(set(labels)))
        self.assertFalse(set(labels) & set(top_ports))

    def test_raw_output_obligation_remains_even_when_fully_independent(self):
        text = live_miter(example()).decode()
        self.assertIn('Queue_2_output_ready: assert property', text)
        self.assertNotIn('Queue_2_live_ready:', text)
        self.assertIn('Queue_2_step_0: assert property', text)
        for p in ('WE', 'WA', 'WD', 'RA0'):
            self.assertIn('Queue_2_memory_' + p, text)

    def test_live_bit_obligation_is_additional(self):
        binding = example()
        binding['cuts']['Queue_2']['ready'].update(width=4, independent_mask=8)
        text = live_miter(binding).decode()
        self.assertIn('Queue_2_output_ready: assert property', text)
        self.assertIn("(reference_Queue_2_ready & 4'd7)", text)
        self.assertIn('Queue_2_live_ready: assert property', text)
        self.assertIn('<embedded>::production_queue_miter.Queue_2_live_ready:precondition1', properties(binding, 'live'))

    def test_changed_inputs_and_missing_obligations_reject(self):
        binding = example()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            inputs = proof_inputs(binding, 'parent')
            for role, file in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
                (path / file).write_bytes(inputs[role])
            changed = copy.deepcopy(binding)
            changed['parents']['Parent']['registers'].clear()
            with self.assertRaisesRegex(FormatError, 'unbound'):
                validate(changed, 'parent', path)
            (path / 'context-results.tsv').write_text('FORMAT\tproduction-context-v1\nEND\n')
            with self.assertRaisesRegex(FormatError, 'identity'):
                validate(binding, 'parent', path)

    def test_whole_hierarchy_keeps_every_register_and_memory_port(self):
        binding = example()
        parent = binding['parents']['Parent']
        binding.update(top='Parent', architecture_source='module Parent(' + parent['header'] + ');' +
                       parent['body'] + 'endmodule\n' + binding['queue_binding']['queues']['Queue_2']['reference_source'],
                       memory_source='module CKMEM_W1_D2_R1(input CP, input WE, input WA, input WD, input RA0, output Q0);\nendmodule\n',
                       semantic_entries=[dict(kind='register', original_path='saved', width=1, state_id='a'),
                                         dict(kind='register', original_path='q.pointer', width=1, state_id='b'),
                                         dict(kind='memory', memory=dict(reads=[{}]))])
        text = whole_miter(binding).decode()
        self.assertIn('reference.q.pointer == implementation.q.pointer', text)
        self.assertIn('reference.saved == implementation.saved', text)
        for port in ('CP', 'WE', 'WA', 'WD', 'RA0'):
            self.assertIn('ckcontext_q_ckcontext_ckmem_ram_' + port + '_equal:', text)
        self.assertIn('ckcontext_inject_q_ready_different:', text)
        self.assertNotIn('CKMEM_W1_D2_R1 ckmem_ram', text)
        self.assertNotRegex(text, r'\b(assume|restrict|initial|force)\b')


if __name__ == '__main__':
    unittest.main()
