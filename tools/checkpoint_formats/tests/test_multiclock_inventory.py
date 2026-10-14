import copy
import hashlib
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.multiclock_inventory import audit_inventory
from tools.checkpoint_formats.semantic import manifest_hash
from tools.checkpoint_formats.tests.test_semantic import example


class EmittedMultiClockInventoryTests(unittest.TestCase):
    def setUp(self):
        self.manifest, _ = example()
        clock = self.manifest.pop('clock_domain')
        clocks = [clock, 'Harness.dut.slow']
        self.manifest.update(manifest_version=3, clock_domains=list(clocks), clock_inputs=list(clocks),
                             clock_aliases=[dict(name='forwarded', source='slow', direction='output')], external_models=[])
        for entry in self.manifest['state']:
            entry['clock_domain'] = clocks[1] if entry['hierarchy'].endswith('b.saved') else clock
        self.boundary = dict(boundary_version=3, dut_module='Inventory', dut_root='Harness.dut',
                             sample_phase='before_clock_event', clock_inputs=list(clocks),
                             clock_aliases=copy.deepcopy(self.manifest['clock_aliases']),
                             ports=[dict(name='data', direction='input', width=9)])
        self.reference = 'complete independently bound reference'
        self.manifest['reference_sha256'] = hashlib.sha256(self.reference.encode()).hexdigest()
        self.clean = '''module Leaf(input clock, input [8:0] data);
  reg [8:0] saved;
  always @(posedge clock) begin
    saved <= data;
  end
endmodule
module Inventory(input clock, input slow, input [8:0] data, output forwarded);
  reg [8:0] sram [0:7];
  wire relayed;
  Leaf a (.clock(clock), .data(data));
  Leaf b (.clock(relayed), .data(data));
  assign relayed = slow;
  assign forwarded = relayed;
  always @(posedge clock) begin
    sram[0] <= data;
  end
endmodule
'''

    def audit(self, clean=None, boundary=None, access=None):
        clean = self.clean if clean is None else clean
        access = access or dict(access_version=1, scope='clean-rtl-inventory-only',
            state_manifest_sha256=manifest_hash(self.manifest), clean_rtl_sha256=hashlib.sha256(clean.encode()).hexdigest(),
            dut_module='Inventory', state=[dict(state_id=e['state_id'], rtl_path=e['hierarchy'][len('Harness.dut.'):])
                                          for e in self.manifest['state']])
        return audit_inventory(self.manifest, boundary or self.boundary, self.reference, clean, access)

    def test_complete_storage_and_actual_clock_blocks_are_independently_audited(self):
        report = self.audit()
        self.assertEqual(report['semantic_words'], 10)
        self.assertTrue(report['complete_emitted_storage_and_clock_ownership'])
        self.assertFalse(report['CPU_level2_verified'])

    def test_missing_or_wrong_clock_ownership_is_not_hidden_by_same_width_state(self):
        for old, new in [('posedge clock', 'posedge slow'), ('relayed = slow', 'relayed = clock'),
                         ('posedge clock', 'posedge data'), ('saved <= data;', ''),
                         ('reg [8:0] saved;', 'reg [9:0] saved;'),
                         ('relayed = slow', 'relayed = relayed'), ('relayed = slow', 'relayed = slow & data')]:
            with self.subTest(change=new), self.assertRaises(FormatError):
                self.audit(self.clean.replace(old, new))

    def test_boundary_source_and_access_binding_reject_changed_or_incomplete_mapping(self):
        boundary = copy.deepcopy(self.boundary)
        boundary['clock_aliases'][0]['source'] = 'clock'
        with self.assertRaises(FormatError):
            self.audit(boundary=boundary)
        for field in ('clock_inputs', 'ports'):
            boundary = copy.deepcopy(self.boundary); boundary[field].pop()
            with self.subTest(field=field), self.assertRaises(FormatError):
                self.audit(boundary=boundary)
        access = dict(access_version=1, scope='clean-rtl-inventory-only',
            state_manifest_sha256=manifest_hash(self.manifest), clean_rtl_sha256=hashlib.sha256(self.clean.encode()).hexdigest(),
            dut_module='Inventory', state=[])
        with self.assertRaises(FormatError):
            self.audit(access=access)


if __name__ == '__main__':
    unittest.main()
