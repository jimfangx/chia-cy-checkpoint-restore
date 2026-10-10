import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, encode
from tools.checkpoint_formats.live_shadow import prepare_live_shadow
from tools.checkpoint_formats.replay import package_capture
from tools.checkpoint_formats.tests.test_replay import fixture


class LiveShadowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.manifest, self.boundary, self.rtl = fixture()
        raw = self.out / 'raw.jsonl'
        raw.write_text('{"cycle":0,"values":["101","102","103","104","105"]}\n')
        package_capture(self.manifest, self.boundary, 'test', raw, 0, 1, self.out / 'capture')
        self.image = (self.out / 'capture/capture.rtlckpt').read_bytes()

    def prepare(self, image=None, boundary=None, transformed=None, out='live'):
        return prepare_live_shadow(self.manifest, boundary or self.boundary, 'test',
                                   image or self.image, self.rtl,
                                   transformed or self.rtl + 'DUT dut();', self.out / out)

    def test_independent_semantic_image_and_live_edge_protocol(self):
        metadata = self.prepare()
        self.assertEqual(metadata['restored_words'], 3)
        self.assertFalse(metadata['level1_restore_integrated'])
        clean = (self.out / 'live/clean.sv').read_text()
        authority = (self.out / 'live/authority.sv').read_text()
        self.assertIn('shadow_receive()', clean)
        self.assertIn('clock = 1;', clean)
        self.assertLess(clean.index('FIRST_MISMATCH'), clean.index('clock = 1;'))
        self.assertLess(clean.index('clock = 1;'), clean.index('ACK %0d", next_cycle));',
                                                          clean.index('clock = 1;')))
        self.assertIn('always @(posedge clock)', authority)
        self.assertNotIn('trace', clean)
        self.assertEqual(len((self.out / 'live/restore.txt').read_text().splitlines()), 3)

    def test_incompatible_or_corrupt_level2_rejects_before_artifact_creation(self):
        corrupt = bytearray(self.image)
        corrupt[-1] ^= 1
        boundary = copy.deepcopy(self.boundary)
        boundary['dut_root'] = 'Harness.other'
        for kwargs in (dict(image=bytes(corrupt)), dict(boundary=boundary),
                       dict(transformed=self.rtl.replace('saved', 'renamed') + 'DUT dut();'),
                       dict(transformed=self.rtl + 'DUT dut(); DUT other();')):
            with self.assertRaises(FormatError):
                self.prepare(**kwargs)
            self.assertFalse((self.out / 'live/restore.txt').exists())
            self.assertFalse((self.out / 'live/clean.sv').exists())

    def test_session_identity_changes_with_actual_image_and_rtl(self):
        first = self.prepare()
        second = self.prepare(transformed=self.rtl + '// comment\nDUT dut();', out='other')
        self.assertNotEqual(first['session_identity'], second['session_identity'])
        # A valid, rechecksummed image with a different logical cycle cannot
        # silently join the old session, even when all state bits are identical.
        from tools.checkpoint_formats.semantic import decode_semantic
        from tools.checkpoint_formats.replay import builds
        build, _ = builds(self.manifest, self.boundary, 'test')
        doc = decode_semantic(self.image, build, self.manifest)
        doc['target_cycle'] = 42
        third = self.prepare(image=encode('rtlckpt', doc), out='third')
        self.assertEqual(third['first_cycle'], 42)
        self.assertNotEqual(first['session_identity'], third['session_identity'])

    def test_unbounded_codec_cycle_cannot_overflow_live_transport(self):
        from tools.checkpoint_formats.semantic import decode_semantic
        from tools.checkpoint_formats.replay import builds
        build, _ = builds(self.manifest, self.boundary, 'test')
        doc = decode_semantic(self.image, build, self.manifest)
        for cycle in (2**64 - 1, 2**64, 2**100):
            doc['target_cycle'] = cycle
            with self.assertRaisesRegex(FormatError, 'target-cycle range'):
                self.prepare(image=encode('rtlckpt', doc))
        self.assertFalse((self.out / 'live').exists())


if __name__ == '__main__':
    unittest.main()
