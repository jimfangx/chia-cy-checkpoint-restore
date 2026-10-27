"""Adversarial checks for the exact whole-host regional source permission."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_native_inplace_annotations import protocol_json
from tools.checkpoint_formats.tests.audit_region_widget_graft import (
    NO_DEDUP, audit_annotations, audit_source_policy, context_snapshot, sha, text_digest)
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules


class RegionalSourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.context = {'class': 'midas.stage.ConfigStringAnnotation', 'configString': 'Original'}
        self.source = [{'class': NO_DEDUP}, {'class': 'firrtl.annotations.MemoryNoSynthInit$'}, self.context]
        self.retained = {'class': 'example.UnsupportedOwner', 'target': '~Original|Original>owner'}
        self.original = self.source + [self.retained]
        for name in ('before-reserved.fir', 'native-inlined.fir'):
            (self.path/name).write_text('circuit Original :\n  module Original :\n    skip\n')
        self.write('host-annotations.json', self.source)
        self.write('before-reserved-annotations.json', self.original)
        self.inventory = {'source_policy': dict(policy_version=1,
            scope='exact_ordered_whole_host_typed_storage_and_inert_context',
            source_annotations_sha256=text_digest(protocol_json(self.source)),
            retained_annotations_sha256=text_digest(protocol_json([self.retained])),
            original_context=context_snapshot([self.context], sha(self.path/'before-reserved.fir'), sha(self.path/'before-reserved.fir')),
            source_context=context_snapshot([self.context], sha(self.path/'native-inlined.fir'), sha(self.path/'native-inlined.fir')))}

    def write(self, name, value):
        (self.path/name).write_text(protocol_json(value))

    def test_original_ordered_projection_and_legacy_policy(self):
        self.assertEqual(audit_source_policy(self.path, self.inventory, self.original), self.inventory['source_policy'])
        self.write('host-annotations.json', [{'class': NO_DEDUP}])
        self.assertIsNone(audit_source_policy(self.path, {}, self.original))

    def test_rehashed_source_omission_reorder_duplicate_and_substitution(self):
        changed = dict(self.context, configString='Foreign')
        for source in (self.source[1:], self.source[::-1], self.source + [self.source[0]],
                       [self.source[0], self.context], self.source[:-1] + [changed]):
            with self.subTest(source=source):
                self.write('host-annotations.json', source)
                doc = copy.deepcopy(self.inventory)
                doc['source_policy']['source_annotations_sha256'] = text_digest(protocol_json(source))
                with self.assertRaisesRegex(FormatError, 'lost/reordered/changed original annotations'):
                    audit_source_policy(self.path, doc, self.original)

    def test_preinline_duplicate_cannot_be_hidden_by_coalescing(self):
        self.write('before-reserved-annotations.json', self.original + [self.context])
        with self.assertRaisesRegex(FormatError, 'duplicate regional compiler context option'):
            audit_source_policy(self.path, self.inventory, self.original)

    def test_permission_cannot_reclassify_or_drop_retained_owner(self):
        for field, value in (('retained_annotations_sha256', text_digest(protocol_json([]))),
                             ('scope', 'complete_capture'), ('policy_version', 2)):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.inventory)
                doc['source_policy'][field] = value
                with self.assertRaisesRegex(FormatError, 'differs from original'):
                    audit_source_policy(self.path, doc, self.original)

    def unknown_execution(self, owner, extra, child):
        def circuit(child, extra):
            return '''circuit Root :
  module Root :
    input clock : Clock
    inst leaf of %s
    inst gate of Native
%s
  module Leaf :
    input clock : Clock
    reg value : UInt<8>, clock
  module BankLeaf :
    input clock : Clock
    reg value : UInt<8>, clock
  extmodule Native :
    input I : Clock
    input CE : UInt<1>
    output O : Clock
    defname = BUFGCE
''' % (child, extra)
        original = parse_modules(circuit('Leaf', ''))
        connected = parse_modules(circuit(child, extra))
        self.assertEqual(original[owner], connected[owner])
        annotations = [{'class': NO_DEDUP},
            {'class': 'midas.passes.HostClockSource', 'target': '~Root|Root>clock'},
            {'class': 'example.UnsupportedOwner', 'target': '~Root|' + owner + ('>CE' if owner == 'Native' else '>value')}]
        self.write('native-inlined-annotations.json', annotations)
        self.write('connected-annotations.json', annotations)
        self.write('host-annotations.json', [{'class': NO_DEDUP}])
        self.write('grafted-annotations.json', [{'class': NO_DEDUP}])
        # All annotation payloads agree. The rejection must follow original
        # versus emitted execution sets, before any sidecar hash checks.
        with self.assertRaisesRegex(FormatError, 'unsupported annotation targets a changed definition'):
            audit_annotations(self.path, original, connected, 'Root', {'host': 'Root'})

    def test_unknown_owner_cannot_lose_specialized_leaf_executions(self):
        self.unknown_execution('Leaf', '', 'BankLeaf')

    def test_unknown_owner_cannot_broaden_to_new_clock_gate_execution(self):
        self.unknown_execution('Native', '    inst mask of Native', 'Leaf')


if __name__ == '__main__':
    unittest.main()
