import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, encode
from tools.checkpoint_formats.finite_replay import package_boundary_trace, prepare_finite_replay
from tools.checkpoint_formats.replay import package_capture
from tools.checkpoint_formats.tests.test_replay import fixture


class FiniteReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.manifest, self.boundary, self.rtl = fixture()
        raw = self.out / 'capture.jsonl'
        raw.write_text('\n'.join('{"cycle":%d,"values":["101","102","103","104","105"]}' % c
                                 for c in range(4)))
        self.checkpoint, self.trace = package_capture(self.manifest, self.boundary, 'test', raw, 1, 3, self.out)

    def prepare(self, boundary=None, trace=None, rtl=None, checkpoint=None):
        return prepare_finite_replay(self.manifest, boundary or self.boundary, 'test',
                                    encode('rtlckpt', checkpoint or self.checkpoint),
                                    encode('trace', trace or self.trace), rtl or self.rtl, self.out / 'replay')

    def test_complete_finite_trace_and_clock_alias(self):
        result = self.prepare()
        self.assertEqual((result['first_cycle'], result['end_cycle'], result['restored_words']), (1, 4, 3))
        self.assertEqual(result['memories'], [dict(path='dut.ram', width=9, depth=2)])
        self.assertEqual(len((self.out / 'replay/trace.txt').read_text().splitlines()), 3)
        # The trace hash binds the original schema, including alias definitions.
        boundary = dict(self.boundary, boundary_version=2,
                        clock_aliases=[dict(name='ep_clock', direction='output', source='clock')])
        rtl = self.rtl.replace('output [8:0] result', 'output ep_clock, output [8:0] result')
        rtl = rtl.replace('endmodule', 'assign ep_clock = clock;\nendmodule')
        from tools.checkpoint_formats.replay import builds
        trace = dict(self.trace, build=builds(self.manifest, boundary, 'test')[1])
        self.prepare(boundary=boundary, trace=trace, rtl=rtl)
        self.assertNotIn('ep_clock', (self.out / 'replay/trace.txt').read_text())
        with self.assertRaisesRegex(FormatError, 'clock alias'):
            self.prepare(boundary=boundary, trace=trace, rtl=rtl.replace('ep_clock = clock', 'ep_clock = 1\'h0'))

    def test_mapping_membership_and_cycle_fail_before_publication(self):
        for mutate in (lambda t: t['records'][0]['inputs'].pop('data'),
                       lambda t: t['records'][0]['outputs']['result'].update(width=10),
                       lambda t: t.update(target_cycle=2, records=t['records'][1:]),
                       lambda t: t.update(records=[])):
            changed = copy.deepcopy(self.trace)
            mutate(changed)
            with self.assertRaises(FormatError):
                self.prepare(trace=changed)
        for rtl in (self.rtl.replace('saved', 'lost'), self.rtl.replace('input [8:0] data', 'input [9:0] data'),
                    self.rtl.replace('endmodule', 'logic unlisted;\nendmodule'),
                    self.rtl.replace('endmodule', 'integer unlisted;\nendmodule'),
                    self.rtl.replace('endmodule', 'always @(posedge data) saved <= data;\nendmodule')):
            with self.assertRaises(FormatError):
                self.prepare(rtl=rtl)
        self.assertFalse((self.out / 'replay').exists())

    def test_recorded_edge_import_and_explicit_rejections(self):
        raw = self.out / 'boundary.txt'
        valid = 'DATA 1 101 102\nDATA 2 101 102\nDATA 3 101 102\n'
        raw.write_text(valid)
        result = package_boundary_trace(self.manifest, self.boundary, 'test', encode('rtlckpt', self.checkpoint),
                                        raw, self.out / 'package')
        self.assertEqual(result['samples'], 3)
        for text in ('', valid.replace('DATA 2', 'DATA 3'), valid.replace('101 102', '101'),
                     valid.replace('101', '10x'), valid.replace('101', '201'), valid + 'END 4\n'):
            raw.write_text(text)
            with self.subTest(text=text), self.assertRaises(FormatError):
                package_boundary_trace(self.manifest, self.boundary, 'test', encode('rtlckpt', self.checkpoint),
                                       raw, self.out / 'bad-package')
        self.assertFalse((self.out / 'bad-package').exists())


if __name__ == '__main__':
    unittest.main()
