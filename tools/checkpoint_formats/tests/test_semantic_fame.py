import copy
import hashlib
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.semantic import manifest_hash
from tools.checkpoint_formats.semantic_fame import audit_mapping
from tools.checkpoint_formats.tests import test_bridge_semantic


class SemanticFAMEMapTests(unittest.TestCase):
    def setUp(self):
        fixture = test_bridge_semantic.BridgeSemanticTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.args = dict(manifest=fixture.manifest, generated=fixture.generated,
                         reference='generated-reference', rtl=fixture.transformed, bufgce='', plusarg='')
        generated = {e['hierarchy']: e for e in fixture.generated['state']}
        self.mapping = dict(map_version=1, scope='semantic-storage-map-only', capture_supported=False,
                            state_manifest_sha256=manifest_hash(fixture.manifest),
                            generated_rtl_sha256=hashlib.sha256(fixture.transformed.encode()).hexdigest(),
                            generated_manifest_sha256=hashlib.sha256(canonical(fixture.generated)).hexdigest(),
                            state=[dict(state_id=e['state_id'], rtl_path='FPGATop.dut.' + e['hierarchy'].split('.')[-1],
                                        generated_state_id=generated['FPGATop.dut.' + e['hierarchy'].split('.')[-1]]['state_id'])
                                   for e in fixture.manifest['state']])

    def test_complete_map_audits_actual_declarations_without_authorizing_capture(self):
        report = audit_mapping(mapping=self.mapping, **self.args)
        self.assertEqual(report['semantic_words'], 3)
        self.assertFalse(report['CPU_level1_verified'])
        self.assertFalse(report['CPU_level2_verified'])

    def test_membership_alias_shape_source_and_scope_rejections(self):
        for mutate in (
            lambda d: d.update(map_version=True), lambda d: d.update(capture_supported=True),
            lambda d: d.update(state_manifest_sha256='0' * 64),
            lambda d: d.update(generated_rtl_sha256='0' * 64),
            lambda d: d.update(generated_manifest_sha256='0' * 64),
            lambda d: d['state'].pop(), lambda d: d['state'].append(copy.deepcopy(d['state'][0])),
            lambda d: d['state'].reverse(), lambda d: d['state'][0].update(rtl_path='FPGATop.absent'),
            lambda d: d['state'][0].update(generated_state_id='0' * 64),
            lambda d: d['state'][0].update(rtl_path=d['state'][1]['rtl_path']),
        ):
            bad = copy.deepcopy(self.mapping); mutate(bad)
            with self.subTest(map=bad), self.assertRaises(FormatError):
                audit_mapping(mapping=bad, **self.args)
        # Even consistently re-hashed generated metadata must match real RTL.
        bad_args = copy.deepcopy(self.args)
        bad_args['generated']['state'][0]['width'] += 1
        bad = copy.deepcopy(self.mapping)
        bad['generated_manifest_sha256'] = hashlib.sha256(canonical(bad_args['generated'])).hexdigest()
        with self.assertRaises(FormatError):
            audit_mapping(mapping=bad, **bad_args)


if __name__ == '__main__':
    unittest.main()
