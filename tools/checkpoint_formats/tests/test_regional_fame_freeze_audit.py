"""Directed independent source/equation checks for the regional FAME auditor."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_regional_fame_freeze import audit, mutation_probes
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules


def fixture(directory):
    registers = [('completed', 64), ('overflow', 1), ('consumed', 64), ('applied', 64), ('pending_flag', 1)]
    ports = '    input clock : Clock\n    input reset : UInt<1>\n    output output_value : UInt<64>\n'
    declarations = ''.join(f'    reg {name} : UInt<{width}>, clock with :\n'
                           f'      reset => (UInt<1>("h0"), {name})\n' for name, width in registers)
    drivers = {name: f'mux(reset, UInt<{width}>("h0"), {name})' for name, width in registers}
    logic = ('    node finishing = UInt<1>("h1")\n'
             '    node consume = finishing\n'
             '    node launch = and(pending_flag, finishing)\n'
             '    node pending = pending_flag\n'
             '    output_value <= completed\n'
             '    gate.I <= clock\n'
             '    gate.CE <= launch\n')
    preamble = ('FIRRTL version 1.2.0\ncircuit Top :\n'
                '  extmodule Native :\n    input I : Clock\n    input CE : UInt<1>\n'
                '    output O : Clock\n    defname = BUFGCE\n\n')
    source = preamble + '  module Model :\n' + ports + '\n    inst gate of Native\n' + declarations + logic + \
        ''.join(f'    {name} <= {value}\n' for name, value in drivers.items()) + \
        '\n  module Top :\n    input clock : Clock\n    input reset : UInt<1>\n\n' + \
        '    inst model of Model\n    model.clock <= clock\n    model.reset <= reset\n'
    bank_declarations = declarations.replace(', clock with :', ', checkpoint_physical_root_gate.O with :')
    actual_logic = logic.replace('gate.CE <= launch', 'gate.CE <= and(checkpoint_physical_ce_0, not(checkpoint_physical_mask))') + \
        '    wire checkpoint_physical_ce_0 : UInt<1>\n    checkpoint_physical_ce_0 <= launch\n'
    actual = preamble + '  module Model :\n' + ports + \
        '    input ckpt_freeze : UInt<1>\n    input checkpoint_physical_mask : UInt<1>\n\n' + \
        '    inst checkpoint_physical_root_gate of Native\n' + \
        '    checkpoint_physical_root_gate.I <= clock\n' + \
        '    checkpoint_physical_root_gate.CE <= not(checkpoint_physical_mask)\n' + \
        '    inst gate of Native\n' + bank_declarations + actual_logic + \
        ''.join(f'    {name} <= mux(ckpt_freeze, {name}, mux(UInt<1>("h0"), {name}, {value}))\n'
                for name, value in drivers.items()) + \
        '\n  module Top :\n    input clock : Clock\n    input reset : UInt<1>\n' + \
        '    input checkpoint_inplace_ckpt_freeze : UInt<1>\n' + \
        '    input checkpoint_inplace_checkpoint_physical_mask : UInt<1>\n\n' + \
        '    inst model of Model\n    model.clock <= clock\n    model.reset <= reset\n' + \
        '    model.ckpt_freeze <= checkpoint_inplace_ckpt_freeze\n' + \
        '    model.checkpoint_physical_mask <= checkpoint_inplace_checkpoint_physical_mask\n'
    roles = {'host_clock': 'clock', 'host_reset': 'reset', 'finishing': 'finishing',
             'completed_steps': 'completed', 'overflow': 'overflow'}
    domain_roles = {'consume': 'consume', 'launch': 'launch', 'pending': 'pending',
                    'consumed': 'consumed', 'applied': 'applied', 'pending_flag': 'pending_flag',
                    'gate_ce': 'CE', 'gate_output': 'O'}
    annotations = [dict(class_='midas.checkpoint.FAMEClockProgressModelAnnotation', model='original-model', domains=['clockA'])]
    for domain, group in [('', roles), ('clockA', domain_roles)]:
        for role, ref in group.items():
            base = '~Top|Top/model:Model' + ('/gate:Native' if role in ('gate_ce', 'gate_output') else '')
            annotations.append(dict(class_='midas.checkpoint.FAMEClockProgressSignalAnnotation',
                                    model='original-model', domain=domain, role=role, target=base + '>' + ref))
    annotations = [{('class' if k == 'class_' else k): v for k, v in row.items()} for row in annotations]
    for name, value in [('host.fir', source), ('instrumented.fir', actual),
                        ('host-annotations.json', json.dumps(annotations)),
                        ('instrumented-annotations.json', json.dumps(annotations)),
                        ('binding.json', json.dumps(dict(target='~Top|Top/model:Model', sideband_ports=[
                            dict(selected='ckpt_freeze', enclosing='checkpoint_inplace_ckpt_freeze')],
                            complete_fpga_capture=False, deployable_capture_image=False)))]:
        (directory / name).write_text(value)


class RegionalFAMEFreezeAudit(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        fixture(self.directory)

    def mutate(self, old, new, filename='instrumented.fir'):
        path = self.directory / filename
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def test_checks_original_owner_and_native_masks(self):
        result = audit(self.directory)
        self.assertEqual(result['roles'], 13)
        self.assertEqual(result['stored_bits'], 194)
        self.assertEqual(result['original_owner_registers'], 5)
        self.assertFalse(result['complete_fpga_capture'])
        self.assertEqual(len(mutation_probes(self.directory)), 8)

    def test_changed_reset_and_clock_declarations_reject(self):
        for before, after in [('reset => (UInt<1>("h0"), completed)', 'reset => (reset, completed)'),
                              ('completed : UInt<64>, checkpoint_physical_root_gate.O', 'completed : UInt<64>, clock')]:
            with self.subTest(after=after):
                fixture(self.directory)
                self.mutate(before, after)
                with self.assertRaisesRegex(FormatError, 'register declaration'):
                    audit(self.directory)

    def test_original_output_driver_and_gate_enable_reject(self):
        for before, after in [('output_value <= completed', 'output_value <= UInt<64>("h0")'),
                              ('checkpoint_physical_ce_0 <= launch', 'checkpoint_physical_ce_0 <= consume')]:
            with self.subTest(after=after):
                fixture(self.directory)
                self.mutate(before, after)
                with self.assertRaises(FormatError):
                    audit(self.directory)

    def test_crossed_regional_freeze_rejects_even_with_arbitrary_hashes(self):
        self.mutate('model.ckpt_freeze <= checkpoint_inplace_ckpt_freeze',
                    'model.ckpt_freeze <= checkpoint_inplace_checkpoint_physical_mask')
        binding = json.loads((self.directory / 'binding.json').read_text())
        binding['instrumented_sha256'] = '0' * 64
        (self.directory / 'binding.json').write_text(json.dumps(binding))
        with self.assertRaisesRegex(FormatError, 'crossed regional freeze'):
            audit(self.directory)

    def test_stale_role_target_and_source_reset_reject(self):
        self.mutate('model:Model>completed', 'model:Missing>completed', 'instrumented-annotations.json')
        with self.assertRaisesRegex(FormatError, 'instance mismatch'):
            audit(self.directory)
        fixture(self.directory)
        self.mutate('completed <= mux(reset,', 'completed <= mux(finishing,', 'host.fir')
        with self.assertRaisesRegex(FormatError, 'original observer reset'):
            audit(self.directory)

    def test_unselected_model_equations_remain_bound_to_original(self):
        original = (self.directory / 'host.fir').read_text()
        owner = parse_modules(original)['Model']['body']
        other = '\n'.join('  ' + line for line in owner.replace('module Model :', 'module Other :').splitlines()) + '\n\n'
        for filename in ('host.fir', 'instrumented.fir'):
            path = self.directory / filename
            text = path.read_text().replace('  module Top :', other + '  module Top :')
            path.write_text(text + '    inst other of Other\n    other.clock <= clock\n    other.reset <= reset\n')
        for filename in ('host-annotations.json', 'instrumented-annotations.json'):
            path = self.directory / filename
            rows = json.loads(path.read_text())
            copied = []
            for row in rows:
                row = dict(row, model='unselected-model')
                if 'target' in row:
                    row['target'] = row['target'].replace('/model:Model', '/other:Other')
                copied.append(row)
            path.write_text(json.dumps(rows + copied))
        self.assertEqual(audit(self.directory)['model_identities'], 2)
        path = self.directory / 'instrumented.fir'
        text = path.read_text().replace(other, other.replace('output_value <= completed', 'output_value <= UInt<64>("h0")'))
        path.write_text(text)
        with self.assertRaisesRegex(FormatError, 'owner equation: output_value'):
            audit(self.directory)

    def test_clocked_effect_must_receive_the_exact_bank_hold(self):
        self.mutate('    node finishing =', '    printf(clock, finishing, "running")\n    node finishing =', 'host.fir')
        self.mutate('    node finishing =', '    printf(checkpoint_physical_root_gate.O, and(finishing, not(ckpt_freeze)), "running")\n    node finishing =')
        audit(self.directory)
        self.mutate('and(finishing, not(ckpt_freeze))', 'finishing')
        with self.assertRaisesRegex(FormatError, 'clocked effect'):
            audit(self.directory)

    def test_mutation_probe_uses_an_actual_connect_when_nodes_are_wires(self):
        for name in ('host.fir', 'instrumented.fir'):
            path = self.directory / name
            text = re.sub(r'^    node (\w+) = (.*)$',
                          lambda m: '    wire ' + m[1] + ' : UInt<1>\n    ' + m[1] + ' <= ' + m[2],
                          path.read_text(), flags=re.M)
            path.write_text(text)
        self.assertEqual(len(mutation_probes(self.directory)), 8)


if __name__ == '__main__':
    unittest.main()
