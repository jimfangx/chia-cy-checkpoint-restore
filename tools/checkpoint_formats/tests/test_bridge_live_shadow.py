import hashlib
import json
from pathlib import Path
import unittest

from tools.checkpoint_formats.bridge_live_shadow import prepare_bridge_authority, prepare_bridge_clean
from tools.checkpoint_formats.bridge_semantic import package_snapshot
from tools.checkpoint_formats.codec import FormatError, encode
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic
from tools.checkpoint_formats.tests import test_bridge_semantic as bridge_fixture


class BridgeLiveTests(unittest.TestCase):
    def setUp(self):
        fixture = bridge_fixture.BridgeSemanticTests()
        fixture.setUp()
        self.addCleanup(fixture.temp.cleanup)
        self.manifest, self.boundary = fixture.manifest, fixture.boundary
        self.mapping = fixture.audit()
        self.erased = dict(source_hashes={n: self.mapping['source_hashes'][n]
                                        for n in ('reference', 'clean', 'transformed')},
                           erased_output_semantics_verified=True, erased_outputs=[], unresolved_inputs=[])
        snapshot, _ = fixture.snapshot(self.mapping)
        image = fixture.out / 'capture.rtlckpt'
        package_snapshot(snapshot, self.manifest, self.boundary, self.mapping, 'test', image)
        self.image = image.read_bytes()
        self.cut = json.loads(Path(str(image) + '.cut.json').read_text())
        self.out = fixture.out / 'live'

    def prepare(self, **changes):
        args = dict(manifest=self.manifest, boundary=self.boundary, mapping=self.mapping, erased=self.erased,
                    configuration='test', image=self.image, cut=self.cut, level1_sha256='a'*64, out=self.out)
        args.update(changes)
        prepare_bridge_authority(args['manifest'], args['boundary'], args['mapping'], args['erased'], args['out'])
        return prepare_bridge_clean(**args)

    def test_real_clock_origin_and_complete_pre_edge_readback(self):
        metadata = self.prepare()
        self.assertEqual((metadata['first_cycle'], metadata['level1_cycle'], metadata['restored_words']), (41, 41, 3))
        authority = (self.out / 'authority.sv').read_text()
        self.assertIn('always @(posedge emul.FPGATop.dut.clock)', authority)
        self.assertLess(authority.index('wait(emul.checkpoint_restore_complete)'), authority.index('cycle=first_cycle'))
        self.assertIn('SHADOW_EDGE_BEFORE_RESTORE', authority)
        clean = (self.out / 'clean.sv').read_text()
        self.assertLess(clean.index('semantic_verify(' , clean.index('initial begin')), clean.index('shadow_open(' , clean.index('initial begin')))
        self.assertLess(clean.index('FIRST_MISMATCH'), clean.index('clock=1;'))
        self.assertLess(clean.index('clock=1;'), clean.index('ACK %0d", next_cycle)', clean.index('clock=1;')))
        self.assertEqual(len((self.out / 'restore.txt').read_text().splitlines()), 3)
        self.assertNotIn('ep_clock', clean)  # The proven forwarded clock is not data.

    def test_missing_input_and_changed_erased_definition_reject(self):
        for change in [dict(boundary_input_bindings=[]), dict(ports=[]), dict(semantic_manifest_sha256='f'*64)]:
            with self.subTest(change=change), self.assertRaises(FormatError):
                self.prepare(mapping=dict(self.mapping, **change))
        for change in [dict(unresolved_inputs=[self.mapping['ports'][0]]),
                       dict(erased_output_semantics_verified=False), dict(source_hashes={})]:
            with self.subTest(change=change), self.assertRaises(FormatError):
                self.prepare(erased=dict(self.erased, **change))
        self.assertFalse(self.out.exists())

    def test_incompatible_checkpoint_or_cycle_origin_never_writes_restore(self):
        for change in [dict(semantic_cycle=42), dict(level1_fased_cycle=True),
                       dict(checkpoint_sha256='f'*64), dict(mapping_sha256='f'*64)]:
            with self.subTest(change=change), self.assertRaises(FormatError):
                self.prepare(cut=dict(self.cut, **change))
        bad = bytearray(self.image)
        bad[-1] ^= 1
        with self.assertRaises(FormatError):
            self.prepare(image=bytes(bad))
        self.assertFalse((self.out / 'restore.txt').exists())

    def test_checkpoint_levels_remain_separately_bound(self):
        first = self.prepare()
        second = self.prepare(level1_sha256='b'*64)
        self.assertNotEqual(first['session_identity'], second['session_identity'])
        build, _ = builds(self.manifest, self.boundary, 'test')
        image = decode_semantic(self.image, build, self.manifest)
        image['target_cycle'] = 2**64-1
        changed = encode('rtlckpt', image)
        with self.assertRaisesRegex(FormatError, 'target-cycle range'):
            self.prepare(image=changed, cut=dict(self.cut, semantic_cycle=2**64-1,
                         checkpoint_sha256=hashlib.sha256(changed).hexdigest()))


if __name__ == '__main__':
    unittest.main()
