import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.production_gate_replay import storage_path, write_spans
from tools.checkpoint_formats.tests.test_production_state_map import example
from tools.checkpoint_formats.production_state_map import compose_entries
from tools.checkpoint_formats.tests.verify_production_gate_replay import corruption_record


class ProductionGateTranslationTests(unittest.TestCase):
    def inputs(self):
        mapping = dict(entries=compose_entries(*example()), gate_storage_words=9, gate_storage_bits=41)
        records = dict(register=dict(values=['3']), memory=dict(values=['00']*8))
        return mapping, records

    def test_complete_span_file_and_escaped_scalar_path(self):
        mapping, records = self.inputs()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'spans'
            self.assertEqual(write_spans(mapping,records,path),2)
            self.assertTrue(path.read_text().endswith('END 9 41\n'))
            self.assertEqual(path.read_text().count('\n00\n'),4)
        self.assertEqual(storage_path(['pipe','saved_reg[1]'],'state'),
                         'production_gate_tb.dut.pipe.saved_reg[1].state')

    def test_duplicate_destinations_never_publish_complete_file(self):
        mapping, records = self.inputs()
        mapping['entries'].append(copy.deepcopy(mapping['entries'][1]))
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(FormatError,'duplicate'):
            write_spans(mapping,records,Path(directory)/'spans')

    def test_partial_array_and_nonidentity_transform_reject(self):
        for field,value in (('address_count',7),('bit_count',4),('bit_transform','reverse')):
            mapping, records = self.inputs()
            mapping['entries'][0]['mapping'][field] = value
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(FormatError,'transformation'):
                write_spans(mapping,records,Path(directory)/'spans')

    def test_missing_physical_storage_rejects(self):
        mapping, records = self.inputs()
        mapping['entries'].pop()
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(FormatError,'incomplete'):
            write_spans(mapping,records,Path(directory)/'spans')

    def test_unsupported_hierarchy_is_never_guessed(self):
        for components,storage in ((['pipe.bad'],'state'),(['saved_reg[-1]'],'state'),(['saved reg'],'state'),(['pipe'],'hidden')):
            with self.subTest(components=components), self.assertRaises(FormatError):
                storage_path(components,storage)

    def test_corruption_report_retains_gate_object_and_is_json_serializable(self):
        memory = self.inputs()[0]['entries'][0]
        record = corruption_record(memory,7)
        # Diagnostic files are filesystem Paths; the reported object is a VPI
        # hierarchy string even after the verifier processes those files.
        diagnostic = Path('invalid-spans/missing_span.spans')
        self.assertIsInstance(record['path'],str)
        self.assertEqual(record['path'],'production_gate_tb.dut.ckmem.contents[7]')
        self.assertNotIn(str(diagnostic),canonical(record).decode())

    def test_corruption_report_rejects_invalid_memory_address(self):
        memory = self.inputs()[0]['entries'][0]
        for address in (-1,8,True):
            with self.subTest(address=address), self.assertRaises(FormatError):
                corruption_record(memory,address)

    def test_corruption_report_requires_a_complete_mapped_array(self):
        memory = self.inputs()[0]['entries'][0]
        memory['mapping']['classification'] = 'unproven'
        with self.assertRaises(FormatError):
            corruption_record(memory,0)


if __name__ == '__main__':
    unittest.main()
