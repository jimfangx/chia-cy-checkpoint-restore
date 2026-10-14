import copy
import unittest

from tools.checkpoint_formats.codec import FormatError, encode
from tools.checkpoint_formats.semantic import decode_semantic, encode_semantic, manifest_hash, validate_manifest
from tools.checkpoint_formats.tests.test_semantic import example


def inventory():
    manifest, doc = example()
    clock = manifest.pop('clock_domain')
    clocks = [clock, 'Harness.dut.slow']
    manifest.update(manifest_version=3, clock_inputs=list(clocks), clock_domains=list(clocks),
                    clock_aliases=[dict(name='forwarded', source='slow', direction='output')], external_models=[])
    manifest['state'][0]['clock_domain'] = clocks[1]
    doc['build']['state_manifest_hash'] = manifest_hash(manifest)
    return manifest, doc


class MultiClockInventoryTests(unittest.TestCase):
    def test_complete_inventory_does_not_authorize_single_clock_image(self):
        manifest, doc = inventory()
        validate_manifest(manifest)
        data = encode('rtlckpt', doc)
        for operation in (lambda: encode_semantic(doc, manifest),
                          lambda: decode_semantic(data, doc['build'], manifest)):
            with self.assertRaisesRegex(FormatError, 'event-phase cut binding'):
                operation()

    def test_unknown_missing_duplicate_unused_and_reshaped_clock_owners_reject(self):
        mutations = [lambda m: m.update(clock_domain='Harness.dut.clock'),
                     lambda m: m.update(clock_domains=[]), lambda m: m.update(clock_inputs=[]),
                     lambda m: m['clock_domains'].reverse(),
                     lambda m: m['clock_domains'].append(m['clock_domains'][0]),
                     lambda m: m['clock_inputs'].append('Harness.dut.child.clock'),
                     lambda m: m['clock_inputs'].append('Other.clock'),
                     lambda m: m['clock_inputs'].__setitem__(0, True),
                     lambda m: m['clock_domains'].pop(),
                     lambda m: m['state'][0].update(clock_domain='initial'),
                     lambda m: m['state'][0].update(clock_domain='Harness.dut.unknown'),
                     lambda m: m['state'][0].update(clock_domain='Harness.dut.clock'),
                     lambda m: m['clock_aliases'][0].update(source='unknown'),
                     lambda m: m['clock_aliases'][0].update(name='clock'),
                     lambda m: m['clock_aliases'][0].update(direction='input'),
                     lambda m: m['clock_aliases'].append(copy.deepcopy(m['clock_aliases'][0]))]
        for mutate in mutations:
            manifest, _ = inventory()
            mutate(manifest)
            with self.subTest(manifest=manifest), self.assertRaises(FormatError):
                validate_manifest(manifest)

    def test_unused_boundary_clock_is_explicit_but_has_no_invented_state(self):
        manifest, _ = inventory()
        manifest['clock_inputs'].append('Harness.dut.unused')
        validate_manifest(manifest)
        manifest['clock_domains'].append('Harness.dut.unused')
        with self.assertRaisesRegex(FormatError, 'unowned'):
            validate_manifest(manifest)


if __name__ == '__main__':
    unittest.main()
