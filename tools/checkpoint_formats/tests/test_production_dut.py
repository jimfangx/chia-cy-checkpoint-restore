import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.production_dut import audit_architecture, extract_architecture, prepare, synthesis_text
from tools.checkpoint_formats.replay import inventory_rtl, modules
from tools.checkpoint_formats.semantic import state_id


RTL = '''module Pipeline(input clock, input reset, input we, input [2:0] address,
input [3:0] data, output [3:0] q, output [3:0] q2);
reg [3:0] mem [0:7];
reg [3:0] pipeline;
wire [2:0] wa = address;
wire [2:0] ra = address;
wire [2:0] ra2 = address ^ 3'd1;
wire [3:0] wd = data;
wire enable = we;
wire [3:0] rd;
wire [3:0] rd2;
assign rd = mem[ra];
assign rd2 = mem[ra2];
assign q = pipeline;
assign q2 = rd2;
always @(posedge clock) begin
  if (enable) begin mem[wa] <= wd; end
  if (reset) begin pipeline <= 0; end else begin pipeline <= rd; end
end
endmodule
'''


def inputs():
    state = [dict(state_id=state_id('Test.dut.' + name, kind), hierarchy='Test.dut.' + name,
                  kind=kind, width=4, depth=depth, signed=False, clock_domain='Test.dut.clock',
                  reset='none' if kind == 'memory' else 'synchronous', bit_order='lsb0',
                  address_order='ascending_zero_based') for name, kind, depth in
             (('mem', 'memory', 8), ('pipeline', 'register', 1))]
    manifest = dict(manifest_version=1, manifest_type='rtlckpt', identity_scheme='pre-fame-state-v1',
                    circuit='Test', dut_root='Test.dut', clock_domain='Test.dut.clock', reference_sha256='0'*64,
                    state=sorted(state, key=lambda s: s['state_id']))
    boundary = dict(boundary_version=1, dut_module='Pipeline', dut_root='Test.dut', clock='clock',
                    sample_phase='before_rising_edge', ports=[dict(name=n, direction=d, width=w) for n, d, w in
                    (('clock', 'input', 1), ('reset', 'input', 1), ('we', 'input', 1), ('address', 'input', 3),
                     ('data', 'input', 4), ('q', 'output', 4), ('q2', 'output', 4))])
    return manifest, boundary


class ProductionArchitectureTests(unittest.TestCase):
    def test_contents_and_pipeline_state_remain_complete_and_unproven(self):
        manifest, boundary = inputs()
        candidate, _, architecture, models, _ = extract_architecture(manifest, boundary, RTL)
        self.assertEqual(candidate['state_bits'], 36)
        self.assertEqual(candidate['restored_words'], 9)
        self.assertEqual({e['state_id'] for e in candidate['entries']}, {e['state_id'] for e in manifest['state']})
        self.assertEqual({e['proof_status'] for e in candidate['entries']}, {'unproven'})
        self.assertEqual(inventory_rtl(modules(architecture + models), 'Pipeline'),
                         {'ckmem_mem.contents': (4, 8, 'memory'), 'pipeline': (4, 1, 'register')})
        self.assertIn('if (WE) contents[WA] <= WD;', models)
        self.assertIn('pipeline <= rd;', architecture)

    def test_nested_write_guards_cannot_be_dropped(self):
        for statement in ('if (reset) begin if (enable) begin mem[wa] <= wd; end end',
                          'if (reset) if (enable) begin mem[wa] <= wd; end',
                          'if (reset) begin pipeline <= 0; end else if (enable) begin mem[wa] <= wd; end'):
            with self.subTest(statement=statement), self.assertRaises(FormatError):
                extract_architecture(*inputs(), RTL.replace('if (enable) begin mem[wa] <= wd; end', statement))

    def test_unknown_access_multiwrite_partial_write_or_clock_rejects(self):
        for rtl in (RTL.replace('assign q2 = rd2;', 'assign q2 = mem[ra];'),
                    RTL.replace('pipeline <= rd;', 'pipeline <= mem[ra];'),
                    RTL.replace('if (enable) begin mem[wa] <= wd; end',
                                'if (enable) begin mem[wa] <= wd; end if (reset) begin mem[ra] <= wd; end'),
                    RTL.replace('mem[wa] <= wd', 'mem[wa][0] <= wd[0]'),
                    RTL.replace('posedge clock', 'negedge clock'),
                    RTL.replace('wire [2:0] wa', 'wire [1:0] wa')):
            with self.subTest(rtl=rtl), self.assertRaises(FormatError):
                extract_architecture(*inputs(), rtl)

    def test_duplicate_modules_missing_semantic_state_and_hidden_state_reject(self):
        manifest, boundary = inputs()
        missing = copy.deepcopy(manifest)
        missing['state'].pop()
        for m, rtl in ((manifest, RTL + RTL), (missing, RTL),
                       (manifest, RTL.replace('reg [3:0] pipeline;', 'reg [3:0] pipeline; reg hidden;'))):
            with self.subTest(rtl=rtl), self.assertRaises(FormatError):
                extract_architecture(m, boundary, rtl)

    def test_rehashed_models_or_forged_proof_status_do_not_authorize_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'architecture'
            prepare(*inputs(), RTL, directory)
            self.assertEqual(audit_architecture(directory)['artifact_type'], 'unproven_synthesis_architecture')
            original = (directory / 'architecture-candidate.json').read_bytes()
            candidate = json.loads(original)
            candidate['entries'][0]['proof_status'] = 'proven'
            (directory / 'architecture-candidate.json').write_text(json.dumps(candidate))
            with self.assertRaises(FormatError):
                audit_architecture(directory)
            (directory / 'architecture-candidate.json').write_bytes(original)
            path = directory / 'memory-models.v'
            path.write_text(path.read_text().replace('if (WE)', 'if (!WE)'))
            with self.assertRaises(FormatError):
                audit_architecture(directory)

    def test_unproven_architecture_cannot_enter_the_gate_loader(self):
        from tools.checkpoint_formats.formal_state_map import gate_deposits
        manifest, boundary = inputs()
        candidate = extract_architecture(manifest, boundary, RTL)[0]
        for pretend_proven in (False, True):
            proposed = copy.deepcopy(candidate)
            if pretend_proven:
                for entry in proposed['entries']:
                    entry['proof_status'] = 'proven'
            with self.subTest(pretend_proven=pretend_proven), self.assertRaisesRegex(FormatError, 'formal build artifacts'):
                gate_deposits(proposed, manifest, {}, {}, b'', {}, 'tb.dut')

    def test_synthesis_preprocessor_retains_logic_and_rejects_unknown_active_macros(self):
        source = '`ifdef RANDOMIZE_REG_INIT\nreg ignored;\n`endif\n`ifndef SYNTHESIS\ninitial ignored=1;\n`endif\nwire kept;\n'
        self.assertEqual(synthesis_text(source).strip(), 'wire kept;')
        for source in ('`include "other.v"\n', '`ifdef SYNTHESIS\nwire a = `UNKNOWN;\n`endif\n',
                       '`ifdef SYNTHESIS\nwire a;\n', '`endif\n', '`define WIDTH 3\n'):
            with self.subTest(source=source), self.assertRaises(FormatError):
                synthesis_text(source)


if __name__ == '__main__':
    unittest.main()
