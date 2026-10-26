import copy
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.verify_transport_control_state import ROOT, RTL, reconstruct


class TransportControlStateTests(unittest.TestCase):
    def setUp(self):
        self.sources = {n.rsplit('/', 1)[-1]: (ROOT/n).read_text() for n in RTL}

    def test_every_sequential_field_is_accounted_for(self):
        for gates in (1, 2, 3, 31, 32, 65, 65535):
            rows = reconstruct(self.sources, gates)
            self.assertEqual(len(rows), 24)
            self.assertEqual(sum(r['width'] for r in rows), 481+gates)
            self.assertEqual([r['relative_path'] for r in rows if r['clock'] == 'negedge clock'],
                             ['physical.freeze_low'])
            self.assertNotIn('transport.dma_data', [r['relative_path'] for r in rows])

    def test_new_or_omitted_register_cannot_disappear_from_readout(self):
        for old, new in [('saved_slot, saved_bank, state}', 'saved_slot, saved_bank}'),
                         ('saved_slot, saved_bank, state}', 'saved_slot, saved_bank, state, state}'),
                         ('reg [3:0] state;', 'reg [3:0] state; reg hidden;'),
                         ('reg [3:0] state;', 'reg [3:0] state; reg hidden; always @(posedge clock) hidden <= reset;')]:
            sources = copy.deepcopy(self.sources)
            sources['CheckpointCaptureTransport.sv'] = sources['CheckpointCaptureTransport.sv'].replace(old, new)
            if 'reg hidden;' in new and 'hidden <=' not in new:
                # A declaration alone is not evidence of a physical register.
                self.assertEqual(len(reconstruct(sources, 3)), 24)
            else:
                with self.assertRaises(FormatError):
                    reconstruct(sources, 3)

    def test_nested_cut_composition_must_remain_complete(self):
        for filename, old, new in [
            ('CheckpointCaptureTransport.sv', '.control_state(cut_control_state)', '.control_state()'),
            ('CheckpointPhysicalCaptureTransport.sv', '{physical_control_state, transport_control_state}',
             '{transport_control_state, physical_control_state}'),
            ('CheckpointPhysicalCaptureTransport.sv', '.control_state(physical_control_state)', '.control_state()')]:
            sources = copy.deepcopy(self.sources)
            self.assertEqual(sources[filename].count(old), 1)
            sources[filename] = sources[filename].replace(old, new)
            with self.assertRaises(FormatError):
                reconstruct(sources, 3)

    def test_changed_mask_edge_is_visible_in_independent_schema(self):
        changed = copy.deepcopy(self.sources)
        changed['CheckpointPhysicalClockCut.sv'] = changed['CheckpointPhysicalClockCut.sv'].replace(
            'always @(negedge clock)', 'always @(posedge clock)')
        original = reconstruct(self.sources, 3)
        altered = reconstruct(changed, 3)
        self.assertNotEqual(original, altered)
        self.assertEqual([r for r in altered if r['clock'] == 'negedge clock'], [])

    def test_reset_corruption_is_visible_and_multiple_writers_reject(self):
        changed = copy.deepcopy(self.sources)
        name = 'CheckpointCaptureTransport.sv'
        changed[name] = changed[name].replace("stream_crc <= 32'hffffffff;", "stream_crc <= 32'hfffffffe;", 1)
        self.assertNotEqual(reconstruct(changed, 3), reconstruct(self.sources, 3))
        changed = copy.deepcopy(self.sources)
        changed[name] = changed[name].replace('endmodule', 'always @(posedge clock) state <= 0;\nendmodule')
        with self.assertRaises(FormatError):
            reconstruct(changed, 3)


if __name__ == '__main__':
    unittest.main()
