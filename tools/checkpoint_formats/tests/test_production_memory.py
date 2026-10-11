import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.production_dut import prepare
from tools.checkpoint_formats.production_memory import (
    SCRIPT, _model_fragment, audit, expected_properties, miter, reconstruct, validate_proof,
)
from tools.checkpoint_formats.production_dut import sha
from tools.checkpoint_formats.tests.test_production_dut import RTL, inputs


class ProductionMemoryProofTests(unittest.TestCase):
    def prepare(self, directory):
        architecture = Path(directory) / 'architecture'
        prepare(*inputs(), RTL, architecture)
        return architecture, reconstruct(architecture)

    def test_complete_original_bindings_and_universal_addresses(self):
        with tempfile.TemporaryDirectory() as directory:
            architecture, binding = self.prepare(directory)
            self.assertEqual(binding['memory_bits'], 32)
            self.assertEqual(binding['memory_words'], 8)
            entry = binding['instances'][0]
            self.assertEqual(entry['fragment']['write']['enable'], 'enable')
            self.assertEqual(entry['fragment']['reads'][1]['address'], 'ra2')
            self.assertFalse(binding['gate_restore_authorized'])
            shape = binding['shapes'][entry['cell']]
            text = miter(shape).decode()
            self.assertIn('input [2:0] WA, watched', text)
            self.assertIn('RA1 == watched', text)
            self.assertNotRegex(text, r'\bassume\b')
            self.assertNotIn('reg ', text)
            self.assertIn('next_reference == next_implementation', text)
            self.assertEqual(sum(k == 'assert' for k, _ in expected_properties(shape).values()), 3)

    def test_rehashed_lost_instance_or_port_binding_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            architecture, binding = self.prepare(directory)
            proof = Path(directory) / 'proof'
            proof.mkdir()
            for mutation in ('lost', 'port', 'state_id', 'authorized'):
                changed = copy.deepcopy(binding)
                if mutation == 'lost':
                    changed['instances'].clear()
                elif mutation == 'port':
                    changed['instances'][0]['fragment']['write']['enable'] = '!enable'
                elif mutation == 'state_id':
                    changed['instances'][0]['state_id'] = '0' * 16
                else:
                    changed['gate_restore_authorized'] = True
                (proof / 'binding.json').write_bytes(canonical(changed))
                with self.subTest(mutation=mutation), self.assertRaisesRegex(FormatError, 'memory binding'):
                    audit(architecture, proof)

    def test_hidden_state_or_changed_memory_behavior_rejects(self):
        cell = 'CKMEM_W4_D8_R2'
        source = (f'module {cell}(input CP, input WE, input [2:0] WA, input [3:0] WD, '
                  'input [2:0] RA0, output [3:0] Q0, input [2:0] RA1, output [3:0] Q1);\n'
                  'reg [3:0] contents [0:7];\nassign Q0 = contents[RA0];\nassign Q1 = contents[RA1];\n'
                  'always @(posedge CP) begin\n  if (WE) contents[WA] <= WD;\nend\nendmodule\n')
        self.assertEqual(_model_fragment(source, cell, 4, 8, 2)['write']['enable'], 'WE')
        for changed in (source.replace('if (WE)', 'if (!WE)'),
                        source.replace('contents[RA1]', 'contents[RA0]'),
                        source.replace('contents[WA] <= WD', "contents[WA] <= WD ^ 4'b1"),
                        source.replace('endmodule', 'reg hidden; endmodule'),
                        source.replace('posedge CP', 'negedge CP')):
            with self.subTest(changed=changed), self.assertRaises(FormatError):
                _model_fragment(changed, cell, 4, 8, 2)

    def test_missing_or_unproven_properties_reject_before_raw_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            _, binding = self.prepare(directory)
            shape = next(iter(binding['shapes'].values()))
            proof = Path(directory) / 'proof'
            proof.mkdir()
            artifacts = dict(binding=canonical(binding), miter=miter(shape), script=SCRIPT.encode())
            for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
                (proof / name).write_bytes(artifacts[role])
            for mutation in ('missing_word', 'missing_read', 'missing_cover', 'unproven'):
                expected = expected_properties(shape)
                if mutation.startswith('missing'):
                    needle = {'missing_word': '.word_step', 'missing_read': '.read_1',
                              'missing_cover': '.bit_3_1'}[mutation]
                    expected.pop(next(p for p in expected if p.endswith(needle)))
                else:
                    expected[next(p for p in expected if p.endswith('.word_step'))] = ('assert', 'undetermined')
                rows = ['FORMAT\tproduction-memory-v1']
                rows += ['INPUT\t' + role + '\t' + sha(data) for role, data in artifacts.items()]
                rows += ['PROPERTY\t' + prop + '\t' + '\t'.join(status) for prop, status in expected.items()]
                (proof / 'memory-results.tsv').write_text('\n'.join(rows + ['END', '']))
                with self.subTest(mutation=mutation), self.assertRaisesRegex(FormatError, 'unproven/vacuous/incomplete'):
                    validate_proof(shape, binding, proof)


if __name__ == '__main__':
    unittest.main()
