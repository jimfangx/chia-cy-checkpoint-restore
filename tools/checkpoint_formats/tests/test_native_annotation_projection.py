import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_native_inplace_annotations import audit, HEADER
from tools.checkpoint_formats.simulator import PLUSARG_MODEL_SHA256
from tools.checkpoint_formats.tests.audit_native_inplace_context import context_row, normalized_context


class NativeAnnotationProjectionTest(unittest.TestCase):
    def test_consumed_context_events_accept_only_matching_optional_nested_class_hints(self):
        for producer, nested in [('firrtl.stage.phases.AddCircuit', 'firrtl.stage.FirrtlFileAnnotation'),
                                 ('firrtl.options.phases.GetIncludes', 'firrtl.options.InputAnnotationFileAnnotation')]:
            event = {'class': 'firrtl.annotations.DeletedAnnotation', 'xFormName': producer,
                     'anno': {'file': 'fixture/input'}}
            hinted = dict(event, anno=dict(event['anno'], **{'class': nested}))
            self.assertEqual(normalized_context(hinted), event)
            self.assertEqual(context_row(hinted), context_row(event))
            self.assertIn('class', hinted['anno'])  # Auditing never rewrites the original evidence.
            for bad in [dict(event, anno=dict(event['anno'], **{'class': 'fixture.HiddenOwner'})),
                        dict(event, xFormName='fixture.UnconsumedInput'),
                        dict(event, anno=dict(event['anno'], extra='uncontracted'))]:
                with self.subTest(event=bad), self.assertRaises(FormatError):
                    context_row(bad)

    def test_context_normalization_does_not_admit_deleted_state_or_unknown_owner_events(self):
        for event in [
            {'class': 'firrtl.annotations.DeletedAnnotation', 'xFormName': 'firrtl.stage.phases.AddCircuit',
             'anno': {'class': 'firrtl.transforms.DontTouchAnnotation', 'target': '~Root|Leaf>value'}},
            {'class': 'fixture.HiddenOwner', 'target': '~Root|Leaf>value'},
        ]:
            with self.subTest(event=event), self.assertRaises(FormatError):
                context_row(event)

    def fixture(self,directory):
        before='''circuit Root :
  module Leaf :
    output out : UInt<5>
    out <= UInt<5>("h7")
  module Root :
    input clock : Clock
    input address : UInt<1>
    output value : UInt<5>
    inst left of Leaf
    inst right of Leaf
    value <= left.out
    mem ram :
      data-type => UInt<8>
      depth => 2
      read-latency => 0
      write-latency => 1
      reader => r
      read-under-write => undefined
    ram.r.addr <= address
    ram.r.en <= UInt<1>(1)
    ram.r.clk <= clock
'''
        after=before.replace('inst left of Leaf','inst left of BankedLeaf')+'''  module BankedLeaf :
    output out : UInt<5>
    out <= UInt<5>("h7")
'''
        constant=dict(target='~Root|Leaf',sourceSHA256=PLUSARG_MODEL_SHA256,
            originalCircuitSHA256='a'*64,width=5,default=7,format='limit=%d')
        anno=lambda kind,**fields:dict({'class':kind},**fields)
        no_dedup=anno('firrtl.transforms.NoCircuitDedupAnnotation$')
        policy=anno('firrtl.passes.memlib.DefaultReadFirstAnnotation$')
        touch=anno('firrtl.transforms.DontTouchAnnotation',target='~Root|Leaf>out')
        memory=anno('midas.targetutils.FirrtlMemModelAnnotation',target='~Root|Root>ram')
        box=anno('midas.core.TargetBoxAnnotation',target='~Root|Root/left:Leaf')
        history=anno('firrtl.transforms.DedupedResult',original='~History|Retired',duplicate='~Root|Root/left:Leaf',index=0.5)
        const=anno('midas.checkpoint.SynthesisPlusArgConstantAnnotation',**constant)
        cache=anno('firrtl.transforms.CombinationalPath',sink='~Root|Root>retired',sources=['~Root|Root>address'])
        constant_text=lambda target:f'SynthesisPlusArgConstantAnnotation({target},{PLUSARG_MODEL_SHA256},'+('a'*64)+',5,7,limit=%d)'
        source_rows=[
          ('CombinationalPath',cache),
          ('DedupedResult(~History|Retired,Some(~Root|Root/left:Leaf),0.5)',history),
          ('DefaultReadFirstAnnotation',policy),
          ('DontTouchAnnotation(~Root|Leaf>out)',touch),
          ('FirrtlMemModelAnnotation(~Root|Root>ram)',memory),
          ('NoCircuitDedupAnnotation',no_dedup),
          (constant_text('~Root|Leaf'),const),
          ('TargetBoxAnnotation(~Root|Root/left:Leaf)',box)]
        after_history=dict(history,duplicate='~Root|Root/left:BankedLeaf')
        actual_rows=[
          ('DedupedResult(~History|Retired,Some(~Root|Root/left:BankedLeaf),0.5)',after_history),
          ('DefaultReadFirstAnnotation',policy),
          ('DontTouchAnnotation(~Root|BankedLeaf>out)',dict(touch,target='~Root|BankedLeaf>out')),
          ('DontTouchAnnotation(~Root|Leaf>out)',touch),
          ('FirrtlMemModelAnnotation(~Root|Root>ram)',memory),
          ('NoCircuitDedupAnnotation',no_dedup),
          (constant_text('~Root|BankedLeaf'),dict(const,target='~Root|BankedLeaf')),
          (constant_text('~Root|Leaf'),const),
          ('TargetBoxAnnotation(~Root|Root/left:BankedLeaf)',dict(box,target='~Root|Root/left:BankedLeaf'))]
        source=[v for k,v in sorted(source_rows)]
        actual=[v for k,v in sorted(actual_rows)]
        dump=lambda value:json.dumps(value,indent=2,separators=(',',':'))
        sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
        mappings=[dict(source=k,targets=[k]) for k in ['DefaultReadFirstAnnotation']]
        mappings += [dict(source=source_rows[1][0],targets=[actual_rows[0][0]]),
            dict(source=source_rows[3][0],targets=['~Root|BankedLeaf>out','~Root|Leaf>out']),
            dict(source=source_rows[4][0],targets=['~Root|Root>ram']),
            dict(source=constant_text('~Root|Leaf'),targets=['~Root|BankedLeaf','~Root|Leaf']),
            dict(source=source_rows[7][0],targets=['~Root|Root/left:BankedLeaf'])]
        projection=dict(projection_version=1,complete_fpga_capture=False,deployable_capture_image=False,
            host_annotations_sha256=sha(dump(source)),generated_annotations_sha256=sha(dump([no_dedup])),
            instrumented_annotations_sha256=sha(dump(actual)),
            host_translation=dict(translation_version=2,source_sha256=sha(dump([a for a in source if a is not cache])),
                                  translated_sha256=sha(dump(actual)),mappings=mappings),
            invalidated_path_caches=['CombinationalPath(~Root|Root>retired,List(~Root|Root>address))'],
            invalidated_generated_path_caches=[])
        for name,body in [('host.fir',before),('instrumented.fir',after),
             ('host-annotations.json',dump(source)),('generated-annotations.json',dump([no_dedup])),
             ('instrumented-annotations.json',dump(actual)),('annotation-projection.json',dump(projection)),
             ('binding.json',dump(dict(target='~Root|Root/left:Leaf',annotation_projection_sha256=sha(dump(projection))))),
             ('instrumented.synthesis.xdc',HEADER),('instrumented.implementation.xdc',HEADER)]:
            (directory/name).write_text(body)
        return actual,projection

    def test_shared_targets_histories_constants_and_retired_caches_are_independent(self):
        with tempfile.TemporaryDirectory() as path:
            directory=Path(path);self.fixture(directory)
            result=audit(directory)
            self.assertEqual(result['source_annotations'],8)
            self.assertEqual(result['projected_annotations'],9)
            self.assertEqual(result['xdc_lines'],0)

    def test_coherently_rehashed_projection_and_cache_corruptions_reject(self):
        for kind in ('stale-box','history-origin','constant-value','memory-kind','cache-loss','unknown-owner','generated-constant'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as path:
                directory=Path(path);actual,projection=self.fixture(directory)
                if kind=='stale-box': next(a for a in actual if a['class'].endswith('TargetBoxAnnotation'))['target']='~Root|Root/left:Leaf'
                elif kind=='history-origin': next(a for a in actual if a['class'].endswith('DedupedResult'))['original']='~History|Different'
                elif kind=='constant-value': next(a for a in actual if 'SynthesisPlusArg' in a['class'])['default']=8
                elif kind=='memory-kind': next(a for a in actual if 'FirrtlMemModel' in a['class'])['target']='~Root|Root>address'
                elif kind=='cache-loss': projection['invalidated_path_caches']=[]
                elif kind=='generated-constant':
                    generated=json.loads((directory/'generated-annotations.json').read_text())
                    forged=dict(next(a for a in actual if 'SynthesisPlusArg' in a['class']),target='~Root|Missing')
                    generated.append(forged);actual.append(forged)
                    text=json.dumps(generated,indent=2,separators=(',',':'))
                    (directory/'generated-annotations.json').write_text(text)
                    projection['generated_annotations_sha256']=hashlib.sha256(text.encode()).hexdigest()
                else: actual.append({'class':'fixture.UnsupportedOwner'})
                dump=lambda value:json.dumps(value,indent=2,separators=(',',':'))
                sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
                (directory/'instrumented-annotations.json').write_text(dump(actual))
                projection['instrumented_annotations_sha256']=sha(dump(actual))
                projection['host_translation']['translated_sha256']=sha(dump(actual))
                (directory/'annotation-projection.json').write_text(dump(projection))
                binding=json.loads((directory/'binding.json').read_text());binding['annotation_projection_sha256']=sha(dump(projection))
                (directory/'binding.json').write_text(dump(binding))
                with self.assertRaises(FormatError):audit(directory)
