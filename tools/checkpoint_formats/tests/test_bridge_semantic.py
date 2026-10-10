import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.bridge_semantic import (
    audit_bridge_mapping, bridge_ports, package_snapshot, prepare_clean_readback,
    prepare_paired_probe, read_snapshot,
)
from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.semantic import manifest_hash
from tools.checkpoint_formats.tests.test_replay import fixture


class BridgeSemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.manifest, self.boundary, rtl = fixture()
        self.manifest['reference_sha256'] = hashlib.sha256(b'reference').hexdigest()
        self.boundary.update(boundary_version=2,
                             clock_aliases=[dict(name='ep_clock', source='clock', direction='output')])
        self.clean = rtl.replace('output [8:0] result)', 'output [8:0] result, output ep_clock)')
        self.clean = self.clean.replace('endmodule', 'assign ep_clock = clock;\nendmodule')
        self.transformed = rtl + 'module FPGATop(input clock);\nDUT dut();\nendmodule\n'
        entries = []
        for e in self.manifest['state']:
            path = 'FPGATop.dut.' + e['hierarchy'].split('.')[-1]
            entries.append(dict(state_id=hashlib.sha256(canonical(dict(hierarchy=path, kind=e['kind'],
                                               namespace='generated-simulator-state-v1'))).hexdigest(),
                                hierarchy=path, kind=e['kind'], width=e['width'], depth=e['depth'],
                                module='DUT', signed=False, clock_expression='clock', reset_expression='none',
                                adapter='firrtl-' + e['kind'] + '-v1', bit_order='lsb0',
                                address_order='ascending_zero_based'))
        self.generated = dict(manifest_version=1, manifest_type='fsckpt-generated',
                              identity_scheme='generated-simulator-state-v1', circuit='FPGATop', root_module='FPGATop',
                              scope='generated_rtl_only', external_runtime_required=True,
                              reference_sha256=hashlib.sha256(b'generated-reference').hexdigest(),
                              instances=[dict(hierarchy='FPGATop', module='FPGATop', implementation_sha256='a'*64),
                                         dict(hierarchy='FPGATop.dut', module='DUT', implementation_sha256='b'*64)],
                              state=sorted(entries, key=lambda e: e['state_id']))

    def audit(self, **changes):
        args = dict(manifest=self.manifest, boundary=self.boundary, reference='reference', clean=self.clean,
                    generated=self.generated, generated_reference='generated-reference',
                    transformed=self.transformed, bufgce='', target_root='FPGATop.dut')
        args.update(changes)
        return audit_bridge_mapping(**args)

    def snapshot(self, mapping):
        header = dict(snapshot_version=1, snapshot_type='independent_semantic_cut',
                      semantic_manifest_sha256=manifest_hash(self.manifest),
                      mapping_sha256=hashlib.sha256(canonical(mapping)).hexdigest(),
                      target_cycle=41, observed_target_edges=41)
        rows = [header] + [dict(state_id=e['state_id'], width=e['width'], depth=e['depth'],
                                values=['101'] * e['depth']) for e in self.manifest['state']]
        path = self.out / 'snapshot.jsonl'
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return path, rows

    def test_complete_independent_state_mapping_and_clock_aliases(self):
        m = self.audit()
        self.assertEqual((m['semantic_entries'], m['semantic_words']), (2, 3))
        self.assertEqual([p['name'] for p in bridge_ports(self.boundary)], ['data', 'result'])
        self.assertTrue(m['emitted_boundary_ports_complete'])
        self.assertFalse(m['live_boundary_adapter_complete'])
        self.assertTrue(all(e['path'].startswith('FPGATop.dut.') for e in m['entries']))
        prepare_paired_probe(self.manifest, m, self.out)
        source = (self.out / 'paired-probe.sv').read_text()
        self.assertIn('checkpoint_settled_event', source)
        self.assertIn('wait(emul.checkpoint_restore_complete)', source)
        self.assertIn('host_edges || target_edges', source)

    def test_missing_boundary_field_is_an_obligation_and_never_reconstructed(self):
        boundary = copy.deepcopy(self.boundary)
        boundary['ports'].append(dict(name='ignored', direction='input', width=2))
        clean = self.clean.replace('input clock,', 'input [1:0] ignored, input clock,')
        m = self.audit(boundary=boundary, clean=clean)
        self.assertEqual(m['missing_transformed_ports'], [dict(name='ignored', direction='input', width=2)])
        self.assertFalse(m['emitted_boundary_ports_complete'])
        self.assertFalse(m['live_boundary_adapter_complete'])

    def test_changed_state_boundary_root_and_reference_reject(self):
        for changes in (dict(reference='wrong'), dict(target_root='FPGATop.other'),
                        dict(clean=self.clean.replace('reg [8:0] saved;', 'reg [7:0] saved;')),
                        dict(transformed=self.transformed.replace('reg [8:0] saved;', '')),
                        dict(clean=self.clean.replace('assign ep_clock = clock;', 'assign ep_clock = data[0];'))):
            with self.assertRaises(FormatError):
                self.audit(**changes)
        boundary = copy.deepcopy(self.boundary)
        boundary['clock_aliases'].append(dict(name='ep_clock', source='clock', direction='output'))
        with self.assertRaises(FormatError):
            self.audit(boundary=boundary)

    def test_independent_snapshot_roundtrip_and_streamed_restore_before_edges(self):
        mapping = self.audit()
        path, rows = self.snapshot(mapping)
        image = self.out / 'capture.rtlckpt'
        package_snapshot(path, self.manifest, self.boundary, mapping, 'test', image)
        cycle = prepare_clean_readback(image.read_bytes(), self.manifest, self.boundary, mapping, 'test', self.out / 'clean')
        self.assertEqual(cycle, 41)
        self.assertEqual(len((self.out / 'clean/restore.txt').read_text().splitlines()), 3)
        self.assertIn('target_edges || clock', (self.out / 'clean/clean.sv').read_text())
        self.assertEqual(read_snapshot(path, self.manifest, mapping)[0], rows[0])

    def test_snapshot_membership_unknown_padding_and_identity_reject(self):
        mapping = self.audit()
        path, rows = self.snapshot(mapping)
        alternatives = []
        for field, value in [('mapping_sha256', 'a'*64), ('target_cycle', True), ('target_cycle', 2**64)]:
            bad = copy.deepcopy(rows); bad[0][field] = value; alternatives.append(bad)
        for field, value in [('values', ['xxx']), ('values', ['fff']), ('width', True), ('depth', True)]:
            bad = copy.deepcopy(rows); bad[1][field] = value; alternatives.append(bad)
        alternatives.extend([rows[:-1], rows + [rows[-1]], [rows[0], *reversed(rows[1:])]])
        for bad in alternatives:
            path.write_text(''.join(json.dumps(row) + '\n' for row in bad))
            with self.assertRaises(FormatError):
                read_snapshot(path, self.manifest, mapping)
        rows[0]['observed_target_edges'] = 40
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        image = self.out / 'independent.rtlckpt'
        package_snapshot(path, self.manifest, self.boundary, mapping, 'test', image)
        cycle = prepare_clean_readback(image.read_bytes(), self.manifest, self.boundary, mapping,
                                      'test', self.out / 'independent-clean')
        self.assertEqual(cycle, 40)
        self.assertEqual(json.loads(Path(str(image) + '.cut.json').read_text())['level1_fased_cycle'], 41)


if __name__ == '__main__':
    unittest.main()
