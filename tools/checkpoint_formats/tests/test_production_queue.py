import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.production_queue import (
    SCRIPT, _cut_source, gate_expr, instances, miter, port_shapes, properties, validate_proof,
)
from tools.checkpoint_formats.formal_state_map import sha


def example():
    header = 'input clock, input reset, input data, output ready'
    body = '''
reg pointer;
wire word;
assign ready = word;
always @(posedge clock) begin
  if (reset) pointer <= 0; else if (data) pointer <= ~pointer;
end
CKMEM_W1_D2_R1 ckmem_ram(.CP(clock), .WE(data), .WA(pointer), .WD(data), .RA0(pointer), .Q0(word));
'''
    mapped = '''module Queue_2(clock, reset, data, ready);
input clock, reset, data;
output ready;
wire clock, reset, data, ready, pointer;
CKDFF pointer_reg(.CP(clock), .D(data), .Q(pointer));
CKMEM_W1_D2_R1 ckmem_ram(.CP(clock), .WE(data), .WA(pointer), .WD(data), .RA0(pointer), .Q0(ready));
endmodule
'''
    spec = dict(module='Queue_2', ports=port_shapes(header, body),
                reference_source=f'module Queue_2({header});{body}endmodule\n', implementation_source=mapped,
                state=[dict(reference_expression='pointer', gate_instance='pointer_reg', xor=0)],
                memory=dict(width=1, depth=2, memory=dict(instance='ckmem_ram')))
    return dict(standard_models='module CKDFF(input CP, input D, output Q);\nreg state;\n'
                'always @(posedge CP) state <= D;\nassign Q = state;\nendmodule\n',
                queues={'Queue_2': spec}, pending_state=[dict(reason='unproven top')])


class ProductionQueueTests(unittest.TestCase):
    def test_interfaces_and_control_syntax(self):
        binding = example()
        spec = binding['queues']['Queue_2']
        self.assertEqual(set(instances(spec['reference_source'].split(';', 1)[1])), {'ckmem_ram'})
        self.assertEqual(port_shapes('clock, reset, data, ready',
                                    'input clock, reset, data; output ready;'), spec['ports'])
        for header, body in [('clock,reset,other', 'input clock,reset;'),
                             ('input clock, input reset, output reg ready', ''),
                             ('input clock, input reset, input clock', '')]:
            with self.subTest(header=header), self.assertRaises(FormatError):
                port_shapes(header, body)

    def test_cut_keeps_all_registers_and_memory_inputs(self):
        binding = example()
        spec = binding['queues']['Queue_2']
        for side in ('reference', 'implementation'):
            text = _cut_source(spec, side)
            self.assertNotIn('CKMEM_', text)
            for port in ('WE', 'WA', 'WD', 'RA0'):
                self.assertIn('assign cut_' + port, text)
        text = miter(binding).decode()
        self.assertIn('reg pointer;', text)
        self.assertIn('CKDFF pointer_reg', text)
        self.assertIn('Queue_2_step_0:', text)
        self.assertIn('Queue_2_output_ready:', text)
        self.assertNotRegex(text, r'\b(assume|restrict|initial|force)\b')
        self.assertEqual(gate_expr('pointer_reg[2]'), '\\pointer_reg[2] .state')
        self.assertEqual(sum(k == 'assert' for k in properties(binding).values()), 6)
        self.assertEqual(sum(k == 'cover' for k in properties(binding).values()), 14)
        self.assertIn('Queue_2_reset_seen:', text)

    def test_missing_undetermined_or_vacuous_evidence_rejects(self):
        binding = example()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            artifacts = dict(binding=canonical(binding), miter=miter(binding), script=SCRIPT.encode())
            for role, filename in [('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')]:
                (path / filename).write_bytes(artifacts[role])
            for mutation in ('missing_step', 'missing_port', 'missing_output', 'missing_precondition',
                             'undetermined', 'vacuous'):
                expected = {p: (k, 'proven' if k == 'assert' else 'covered') for p, k in properties(binding).items()}
                suffix = dict(missing_step='_step_0', missing_port='_memory_WA', missing_output='_output_ready',
                              missing_precondition='_step_0:precondition1', undetermined='_step_0',
                              vacuous='_step_0:precondition1')[mutation]
                prop = next(p for p in expected if p.endswith(suffix))
                if mutation.startswith('missing'):
                    del expected[prop]
                else:
                    expected[prop] = expected[prop][0], 'undetermined' if mutation == 'undetermined' else 'unreachable'
                lines = ['FORMAT\tproduction-queue-v1']
                lines += ['INPUT\t' + r + '\t' + sha(a) for r, a in artifacts.items()]
                lines += ['PROPERTY\t' + p + '\t' + k + '\t' + s for p, (k, s) in expected.items()]
                (path / 'queue-results.tsv').write_text('\n'.join(lines + ['END', '']))
                with self.subTest(mutation=mutation), self.assertRaisesRegex(FormatError, 'obligation'):
                    validate_proof(binding, path)

    def test_rehashed_removed_state_or_authority_rejects(self):
        binding = example()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for changed in (dict(binding, gate_restore_authorized=True),
                            dict(binding, queues={}), copy.deepcopy(binding)):
                if changed == binding:
                    changed['queues']['Queue_2']['state'].clear()
                (path / 'binding.json').write_bytes(canonical(changed))
                with self.assertRaisesRegex(FormatError, 'unbound'):
                    validate_proof(binding, path)


if __name__ == '__main__':
    unittest.main()
