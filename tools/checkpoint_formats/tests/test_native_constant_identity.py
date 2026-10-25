import copy
import hashlib
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.simulator import PLUSARG_MODEL_SHA256, validate_generated_manifest
from tools.checkpoint_formats.tests.audit_native_inplace_identity import validate_native_constants
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.test_simulator import fixture


class NativeConstantIdentityTest(unittest.TestCase):
    def fixture(self):
        manifest = fixture()
        modules = parse_modules('''circuit Top :
  module Reader :
    output out : UInt<5>
    out <= UInt<5>("h7")
''')
        adapter = dict(adapter='fpga-synthesis-plusarg-constant-v1', source_sha256=PLUSARG_MODEL_SHA256,
                       original_circuit_sha256='b'*64, width=5, default=7, format='limit=%d')
        for name in ('a','b'):
            manifest['instances'].append(dict(hierarchy='Top.'+name, module='Reader',
                external_adapter=copy.deepcopy(adapter),
                implementation_sha256=hashlib.sha256(modules['Reader']['body'].encode()).hexdigest()))
        annotations = [dict(class_='midas.checkpoint.SynthesisPlusArgConstantAnnotation', target='~Top|Reader',
            sourceSHA256=PLUSARG_MODEL_SHA256, originalCircuitSHA256='b'*64, width=5, default=7, format='limit=%d')]
        annotations[0]['class'] = annotations[0].pop('class_')
        return manifest,modules,annotations

    def test_concrete_shared_constant_is_stateless_and_never_admitted_as_metasim_state(self):
        manifest,modules,annotations = self.fixture()
        retained = copy.deepcopy(manifest)
        self.assertEqual(validate_native_constants(manifest,modules,annotations),2)
        self.assertEqual(manifest,retained)
        with self.assertRaises(FormatError): validate_generated_manifest(manifest)

    def test_source_annotation_definition_and_inventory_corruptions_reject(self):
        for name in ('source','origin','width','default','format','unknown-field','missing-annotation',
                     'duplicate-annotation','foreign-annotation','body','hidden-state','implementation',
                     'coherent-default','missing-adapter','mixed-origin','runtime-owner'):
            with self.subTest(name=name):
                manifest,modules,annotations = self.fixture()
                adapter = manifest['instances'][1]['external_adapter']
                if name=='source': adapter['source_sha256']='0'*64
                elif name=='origin': adapter['original_circuit_sha256']='invalid'
                elif name=='width': adapter['width']=True
                elif name=='default': adapter['default']=32
                elif name=='format': adapter['format']='unsafe=%s'
                elif name=='unknown-field': adapter['stateful']=False
                elif name=='missing-annotation': annotations=[]
                elif name=='duplicate-annotation': annotations += copy.deepcopy(annotations)
                elif name=='foreign-annotation': annotations[0]['target']='~Elsewhere|Reader'
                elif name in ('body','hidden-state'):
                    modules['Reader']['body'] += ('\n  out <= UInt<5>("h8")' if name=='body' else '\n  reg hidden : UInt<1>, clock')
                elif name=='implementation': manifest['instances'][1]['implementation_sha256']='0'*64
                elif name=='coherent-default':
                    for row in manifest['instances'][1:]: row['external_adapter']['default']=8
                    annotations[0]['default']=8
                elif name=='missing-adapter':
                    for row in manifest['instances'][1:]: del row['external_adapter']
                elif name=='mixed-origin':
                    manifest['instances'][2]['external_adapter']['original_circuit_sha256']='c'*64
                else: manifest['state'][0]['hierarchy']='Top.a.ghost'
                with self.assertRaises(FormatError): validate_native_constants(manifest,modules,annotations)
