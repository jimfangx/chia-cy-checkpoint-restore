import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_external_owners import audit


class ExternalOwnersTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.text='''circuit Top :
  extmodule Physical :
    input I : Clock
    input CE : UInt<1>
    output O : Clock
    defname = BUFGCE

  extmodule Dead :
    defname = Unknown

  module Child :
    inst gate of Physical

  module Top :
    inst a of Child with { flip clock : Clock} connected to (clock)
    inst b of Child
'''
        sha=lambda t:hashlib.sha256(t.encode()).hexdigest()
        self.manifest=dict(circuit='Top',root_module='Top',reference_sha256=sha(self.text),instances=[
            dict(hierarchy=p,module=m) for p,m in [('Top','Top'),('Top.a','Child'),('Top.b','Child'),
                                                 ('Top.a.gate','Physical'),('Top.b.gate','Physical')]])
        physical=dict(module='Physical',defname='BUFGCE',inline_sources=[],definition_sha256=sha(
            'extmodule Physical :\n  input I : Clock\n  input CE : UInt<1>\n  output O : Clock\n  defname = BUFGCE'))
        self.report=dict(audit_version=1,scope='external_owner_admission_only',root_module='Top',
            reference_sha256=sha(self.text),complete_fpga_capture=False,deployable_capture_image=False,
            reachable_external_instances=[dict(**physical,hierarchy=p,physical_primitive=True,
                physical_capture_binding='unsupported',requires_explicit_owner=True) for p in ['Top.a.gate','Top.b.gate']],
            unused_external_definitions=[dict(module='Dead',defname='Unknown',inline_sources=[],
                definition_sha256=sha('extmodule Dead :\n  defname = Unknown'))])

    def run_audit(self,report=None,manifest=None,text=None):
        for name,data in [('manifest.json',self.manifest if manifest is None else manifest),
                          ('report.json',self.report if report is None else report)]:
            (self.root/name).write_text(json.dumps(data))
        (self.root/'reference.fir').write_text(self.text if text is None else text)
        return audit(self.root/'reference.fir',self.root/'manifest.json',self.root/'report.json')

    def test_repeated_and_connector_instances(self):
        result=self.run_audit()
        self.assertEqual(result['complete_instance_count'],5)
        self.assertEqual(result['physical_primitive_instances'],['Top.a.gate','Top.b.gate'])
        self.assertFalse(result['physical_fpga_capture'])

    def test_missing_duplicate_reordered_external_owners(self):
        for rows in [self.report['reachable_external_instances'][:1],
                     self.report['reachable_external_instances']*2,
                     list(reversed(self.report['reachable_external_instances']))]:
            d=copy.deepcopy(self.report);d['reachable_external_instances']=rows
            with self.assertRaises(FormatError):self.run_audit(report=d)

    def test_primitive_name_or_definition_corruption(self):
        for key,value in [('definition_sha256','0'*64),('defname','AbstractClockGate'),('module','Dead')]:
            d=copy.deepcopy(self.report);d['reachable_external_instances'][0][key]=value
            with self.assertRaises(FormatError):self.run_audit(report=d)

    def test_incomplete_or_forged_manifest(self):
        for rows in [self.manifest['instances'][:-1],self.manifest['instances']*2]:
            d=copy.deepcopy(self.manifest);d['instances']=rows
            with self.assertRaises(FormatError):self.run_audit(manifest=d)

    def test_unused_definitions_are_not_live_owners(self):
        for rows in [[],self.report['unused_external_definitions']*2]:
            d=copy.deepcopy(self.report);d['unused_external_definitions']=rows
            with self.assertRaises(FormatError):self.run_audit(report=d)

    def test_fabricated_capture_or_adapter_rejects(self):
        for key in ['complete_fpga_capture','deployable_capture_image']:
            d=copy.deepcopy(self.report);d[key]=True
            with self.assertRaises(FormatError):self.run_audit(report=d)
        for key,value in [('physical_primitive',False),('requires_explicit_owner',False),
                          ('physical_capture_binding','metasim-bufgce-v1')]:
            d=copy.deepcopy(self.report);d['reachable_external_instances'][0][key]=value
            with self.assertRaises(FormatError):self.run_audit(report=d)

    def test_reference_and_cut_root_binding(self):
        with self.assertRaises(FormatError):self.run_audit(text=self.text+'\n')
        d=copy.deepcopy(self.report);d['root_module']='Child'
        with self.assertRaises(FormatError):self.run_audit(report=d)

    def test_malformed_inline_provenance(self):
        for source in [dict(circuit='Other',filename='gate.v',source_sha256='a'*64),
                       dict(circuit='Top',filename='gate.v',source_sha256='bad')]:
            d=copy.deepcopy(self.report);d['unused_external_definitions'][0]['inline_sources']=[source]
            with self.assertRaises(FormatError):self.run_audit(report=d)
