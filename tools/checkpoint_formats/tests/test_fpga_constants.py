import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_fpga_constants import audit, digest, MODEL_SHA256, PREFIX, SCOPE


class FPGAConstantsAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = '''FIRRTL version 1.2.0
circuit Top :
  extmodule Plus :
    output out : UInt<9>
    defname = plusarg_reader
    parameter WIDTH = 9
    parameter DEFAULT = 341
    parameter FORMAT = "test=%d"

  module Top :
    input clock : Clock
    inst a of Plus
    inst b of Plus
'''
        self.prepared = self.original.replace('''  extmodule Plus :
    output out : UInt<9>
    defname = plusarg_reader
    parameter WIDTH = 9
    parameter DEFAULT = 341
    parameter FORMAT = "test=%d"''', '''  module Plus :
    output out : UInt<9>
    out <= UInt<9>("h155")''')
        model = (Path(__file__).resolve().parents[3] /
                 'sims/firesim/sim/rocket-chip/src/main/resources/vsrc/plusarg_reader.v').read_text()
        self.assertEqual(digest(model), MODEL_SHA256)
        self.sources = [dict(**{'class': 'firrtl.transforms.BlackBoxInlineAnno'}, target='Top.Plus',
                             name='plusarg_reader.v', text=model)]
        definition = self.original.split('  extmodule Plus :\n')[1].split('\n\n')[0]
        definition = 'extmodule Plus :\n'+'\n'.join(s[2:] for s in definition.splitlines())
        self.report = dict(preparation_version=1, scope=SCOPE, root_module='Top', complete_fpga_capture=False,
                           deployable_capture_image=False, external_runtime_required=True,
                           constants=[dict(module='Plus', source_sha256=MODEL_SHA256,
                                           original_definition_sha256=digest(definition), width=9, default=341,
                                           format='test=%d', reachable_instances=['Top.a', 'Top.b'])])

    def run_audit(self, report=None, original=None, prepared=None, sources=None):
        values = {'original.fir': self.original if original is None else original,
                  'prepared.fir': self.prepared if prepared is None else prepared,
                  'sources.json': json.dumps(self.sources if sources is None else sources)}
        doc = copy.deepcopy(self.report if report is None else report)
        doc.update(original_reference_sha256=digest(values['original.fir']),
                   prepared_reference_sha256=digest(values['prepared.fir']),
                   inline_sources_sha256=digest(values['sources.json']))
        values['preparation.json'] = json.dumps(doc)
        values['emission.json'] = json.dumps(dict(binding_version=1, scope=SCOPE, complete_fpga_capture=False,
            deployable_capture_image=False, emitted_verilog_sha256=digest('module Top; endmodule\n'),
            inputs={PREFIX+k: digest(v) for k, v in values.items()}))
        values['emitted.sv'] = 'module Top; endmodule\n'
        for name, text in values.items():
            (self.root/name).write_text(text)
        return audit(*(self.root/n for n in ['original.fir', 'prepared.fir', 'sources.json',
                                             'preparation.json', 'emission.json', 'emitted.sv']))

    def test_complete_repeated_constant_owners(self):
        result = self.run_audit()
        self.assertEqual(result['reachable_constant_instances'], 2)
        self.assertEqual(result['complete_instance_count'], 3)
        self.assertFalse(result['physical_fpga_capture'])

    def test_missing_reordered_duplicate_and_foreign_instance_bindings(self):
        for paths in [[], ['Top.a'], ['Top.b', 'Top.a'], ['Top.a', 'Top.a'], ['Other.a', 'Top.b']]:
            report = copy.deepcopy(self.report)
            report['constants'][0]['reachable_instances'] = paths
            with self.assertRaises(FormatError): self.run_audit(report=report)

    def test_rehashed_changed_prepared_value_or_hidden_owner(self):
        for prepared in [self.prepared.replace('"h155"', '"h154"'),
                         self.prepared.replace('    out <=', '    reg hidden : UInt<1>, clock\n    out <='),
                         self.prepared.replace('    inst b of Plus', '    inst b of Plus\n    reg hidden : UInt<1>, clock')]:
            with self.assertRaises(FormatError): self.run_audit(prepared=prepared)

    def test_rehashed_changed_original_parameters_or_ports(self):
        for original in [self.original.replace('DEFAULT = 341', 'DEFAULT = 340'),
                         self.original.replace('WIDTH = 9', 'WIDTH = 10'),
                         self.original.replace('test=%d', 'test=%h'),
                         self.original.replace('    defname', '    input hidden : UInt<1>\n    defname')]:
            with self.assertRaises(FormatError): self.run_audit(original=original)

    def test_rehashed_changed_sources_or_foreign_target(self):
        for key, value in [('text', self.sources[0]['text']+'\n'), ('target', 'Other.Plus'),
                           ('class', 'unknown'), ('target', 'Top.Other')]:
            sources = copy.deepcopy(self.sources); sources[0][key] = value
            with self.assertRaises(FormatError): self.run_audit(sources=sources)
        with self.assertRaises(FormatError): self.run_audit(sources=[])
        with self.assertRaises(FormatError): self.run_audit(sources=self.sources*2)

    def test_omitted_duplicate_and_forged_definition_report(self):
        for rows in [[], self.report['constants']*2]:
            report = copy.deepcopy(self.report); report['constants'] = rows
            with self.assertRaises(FormatError): self.run_audit(report=report)
        for key, value in [('source_sha256', 'a'*64), ('original_definition_sha256', 'b'*64),
                           ('module', 'Missing'), ('width', 8), ('default', 340), ('format', 'test=%h')]:
            report = copy.deepcopy(self.report); report['constants'][0][key] = value
            with self.assertRaises(FormatError): self.run_audit(report=report)

    def test_capture_claims_and_root_changes_reject(self):
        for key, value in [('complete_fpga_capture', True), ('deployable_capture_image', True),
                           ('external_runtime_required', False), ('root_module', 'Plus')]:
            report = copy.deepcopy(self.report); report[key] = value
            with self.assertRaises(FormatError): self.run_audit(report=report)

    def test_rehashed_hierarchy_or_definition_changes_reject(self):
        for original in [self.original.replace('inst b of Plus', 'inst b of Missing'),
                         self.original.replace('inst b of Plus', 'inst a of Plus'),
                         self.original.replace('inst b of Plus', 'inst b of Top'),
                         self.original+self.original.split('circuit Top :\n')[1]]:
            with self.assertRaises(FormatError): self.run_audit(original=original)
