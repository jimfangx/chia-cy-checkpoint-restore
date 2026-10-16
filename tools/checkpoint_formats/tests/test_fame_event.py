import copy
import unittest

from tools.checkpoint_formats.codec import FormatError, decode
from tools.checkpoint_formats.fame_event import audit_event_boundary, package_window
from tools.checkpoint_formats.semantic import decode_semantic
from tools.checkpoint_formats.tests.test_multiclock_replay import example


class FAMEEventWindowTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.boundary, self.ckpt, self.trace = example()
        counts = dict(self.trace['event_phase']['rising_edges'])
        levels = dict(self.trace['event_phase']['clock_levels'])
        self.rows = []
        for record in self.trace['records']:
            self.rows.append(dict(record, before=dict(levels), rising_edges=dict(counts)))
            for c in levels:
                counts[c] += int(not levels[c] and record['clock_levels'][c])
            levels = dict(record['clock_levels'])
        self.values = [v for e in self.ckpt['records'] for v in e['values']]

    def test_window_retains_actual_counts_and_complete_original_state(self):
        data, trace = package_window(self.manifest, self.boundary, 'test', self.rows, self.values)
        self.assertEqual(decode_semantic(data, self.ckpt['build'], self.manifest), self.ckpt)
        self.assertEqual(decode(trace, 'trace', self.trace['build']), self.trace)

    def test_incomplete_state_event_phase_boundary_and_actual_alias_reject(self):
        for mutate in [lambda r: r[0]['before'].update({next(iter(r[0]['before'])): 1}),
                       lambda r: r[1]['rising_edges'].update({next(iter(r[1]['rising_edges'])): 99}),
                       lambda r: r[1].update(event_index=99), lambda r: r[1].update(cycle=99),
                       lambda r: r[0]['inputs'].pop('data'), lambda r: r[1]['outputs'].pop('out'),
                       lambda r: r[0]['outputs']['forwarded'].update(value='1'),
                       lambda r: r[0]['clock_levels'].update(unknown=0),
                       lambda r: r[0].update(clock_levels=dict(r[0]['before'])),
                       lambda r: r[0]['clock_levels'].update({next(iter(r[0]['clock_levels'])): False})]:
            bad = copy.deepcopy(self.rows); mutate(bad)
            with self.subTest(rows=bad), self.assertRaises(FormatError):
                package_window(self.manifest, self.boundary, 'test', bad, self.values)
        for bad in (self.values[:-1], self.values + ['0'], ['x'] + self.values[1:]):
            with self.assertRaises(FormatError):
                package_window(self.manifest, self.boundary, 'test', self.rows, bad)

    def test_actual_boundary_and_every_storage_clock_require_matching_ownership(self):
        rtl = '''module Leaf(input clock, input [8:0] data, output [8:0] out);
  reg [8:0] saved;
  always @(posedge clock) begin
    saved <= data;
  end
  assign out = saved;
endmodule
module Dut(input clock, input slow, input [8:0] data, output [8:0] out, output forwarded);
  wire [8:0] av;
  wire [8:0] bv;
  reg [8:0] sram [0:7];
  Leaf a (.clock(slow), .data(data), .out(av));
  Leaf b (.clock(clock), .data(data), .out(bv));
  always @(posedge clock) begin
    sram[0] <= data;
  end
  assign out = av;
  assign forwarded = slow;
endmodule
module Parent(input hclock, input ce0, input ce1, input [8:0] data, output [8:0] out);
  wire c0;
  wire c1;
  wire forwarded;
  BUFGCE g0 (.I(hclock), .CE(ce0), .O(c0));
  BUFGCE g1 (.I(hclock), .CE(ce1), .O(c1));
  Dut dut (.clock(c0), .slow(c1), .data(data), .out(out), .forwarded(forwarded));
endmodule
'''
        gate = '''module BUFGCE(input I, input CE, output reg O);
  always @(posedge I or negedge I) begin
    O = CE ? I : 1'b0;
  end
endmodule
'''
        mapping = dict(state=[dict(state_id=e['state_id'], rtl_path='Parent.dut.' +
                                  e['hierarchy'][len(self.manifest['dut_root'])+1:]) for e in self.manifest['state']])
        def audit(source):
            return audit_event_boundary(self.manifest, self.boundary, mapping,
                                        dict(root_module='Parent'), source, gate, '')
        report = audit(rtl)
        self.assertEqual(report['semantic_entries'], 3)
        self.assertEqual(report['clocks'], {'Harness.dut.clock': 'Parent.g0.O', 'Harness.dut.slow': 'Parent.g1.O'})
        self.assertEqual(report['boundary_ports'], 5)
        for bad in [rtl.replace('a (.clock(slow)', 'a (.clock(clock)'),
                    rtl.replace('assign forwarded = slow;', 'assign forwarded = clock;'),
                    rtl.replace('output [8:0] out, output forwarded', 'output [7:0] out, output forwarded'),
                    rtl.replace('Dut dut (', 'Dut copy (.clock(c0), .slow(c1), .data(data), .out(out), .forwarded(forwarded));\n  Dut dut ('),
                    rtl.replace('always @(posedge clock) begin', 'always @(posedge absent) begin', 1),
                    rtl.replace('sram[0] <= data;', 'absent[0] <= data;')]:
            with self.subTest(source=bad), self.assertRaises(FormatError):
                audit(bad)


if __name__ == '__main__':
    unittest.main()
