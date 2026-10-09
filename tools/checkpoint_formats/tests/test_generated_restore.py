import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.generated_restore import prepare_generated_loader, prepare_generated_restore
from tools.checkpoint_formats.simulator import generated_capture, generated_words
from tools.checkpoint_formats.tests.test_simulator import fixture


class GeneratedRestoreTest(unittest.TestCase):
    def test_clock_inventory_requires_resolvable_emitted_sensitivities(self):
        manifest = fixture()
        manifest['state'][0]['clock_expression'] = 'memory-port-clocks'
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with self.assertRaises(FormatError):
                prepare_generated_loader(manifest, 'a'*64, out, 'tb.Top')
            rtl = 'module Top(input clock); reg memory_clk; always @(posedge memory_clk) begin end endmodule'
            prepare_generated_loader(manifest, 'a'*64, out, 'tb.Top', rtl=rtl)
            self.assertIn('"tb.Top.memory_clk"', (out/'generated-restore-table.h').read_text())
            with self.assertRaises(FormatError):
                prepare_generated_loader(manifest, 'a'*64, out, 'tb.Top',
                    rtl=rtl.replace('posedge memory_clk', 'posedge (clock & memory_clk)'))

    def test_high_bufgce_output_rejects_before_publication(self):
        manifest = fixture()
        gate = copy.deepcopy(manifest['state'][0])
        gate.update(hierarchy='Top.gate.O', module='BUFGCE', kind='register',
                    width=1, depth=1, adapter='metasim-bufgce-v1')
        gate['state_id'] = hashlib.sha256(canonical(dict(hierarchy=gate['hierarchy'],
            kind='register', namespace='generated-simulator-state-v1'))).hexdigest()
        manifest['instances'].append(dict(hierarchy='Top.gate', module='BUFGCE',
                                          implementation_sha256='b'*64))
        manifest['state'] = sorted([*manifest['state'], gate], key=lambda e:e['state_id'])
        capture = generated_capture(manifest, ['0'*((w['width']+3)//4) for w in generated_words(manifest)], 7)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            prepare_generated_loader(manifest, 'a'*64, out, 'tb.Top')
            self.assertIn('"tb.Top.gate.I"', (out/'generated-restore-table.h').read_text())
            self.assertIn('"tb.Top.gate.O"', (out/'generated-restore-table.h').read_text())
            prepare_generated_restore(manifest, capture, 'a'*64, out/'low', 'tb.Top')
            next(r for r in capture['records'] if r['owner']=='Top.gate.O')['value']='1'
            with self.assertRaises(FormatError):
                prepare_generated_restore(manifest, capture, 'a'*64, out/'high', 'tb.Top')
            self.assertFalse((out/'high').exists())

    def test_complete_wide_memory_staging_and_entry_bounded_table(self):
        manifest = fixture()
        words = list(generated_words(manifest))
        capture = generated_capture(manifest, [f"{(1 << w['width']) - 1:0{(w['width']+3)//4}x}"
                                               for w in words], 7)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            self.assertEqual(prepare_generated_loader(manifest, 'a'*64, out, 'tb.Top'), 3)
            self.assertEqual(prepare_generated_restore(manifest, capture, 'a'*64, out/'load', 'tb.Top'), 3)
            text = (out/'load').read_text()
            self.assertIn('tb.Top.fifo[1] 9 1ff', text)
            self.assertIn('tb.Top.counter 257 1' + 'f'*64, text)
            self.assertIn('"tb.Top.fifo", 9, 2, true', (out/'generated-restore-table.h').read_text())

    def test_incompatible_or_incomplete_capture_never_creates_or_overwrites(self):
        manifest = fixture()
        capture = generated_capture(manifest, ['0'*((w['width']+3)//4) for w in generated_words(manifest)], 7)
        mutations = [
            lambda c: c.update(capture_version=True),
            lambda c: c.update(external_runtime_required=False),
            lambda c: c.update(manifest_sha256='0'*64),
            lambda c: c.update(sample_phase='settled_host_posedge_parked_driver'),
            lambda c: c.update(host_sample=True),
            lambda c: c['records'].pop(),
            lambda c: c['records'].append(copy.deepcopy(c['records'][-1])),
            lambda c: c['records'].reverse(),
            lambda c: c['records'][-1].update(owner='Top.absent'),
            lambda c: c['records'][-1].update(width=True),
            lambda c: c['records'][-1].update(value='x'),
            lambda c: c['records'][-1].update(value='f'*100),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'load'
            for mutation in mutations:
                altered = copy.deepcopy(capture)
                mutation(altered)
                with self.assertRaises(FormatError):
                    prepare_generated_restore(manifest, altered, 'a'*64, path)
                self.assertFalse(path.exists())
                path.write_text('existing')
                with self.assertRaises(FormatError):
                    prepare_generated_restore(manifest, altered, 'a'*64, path)
                self.assertEqual(path.read_text(), 'existing')
                path.unlink()
            for root in ('tb.Top;escape', '', 'tb..Top'):
                with self.assertRaises(FormatError):
                    prepare_generated_loader(manifest, 'a'*64, Path(directory), root)
                with self.assertRaises(FormatError):
                    prepare_generated_restore(manifest, capture, 'a'*64, path, root)


if __name__ == '__main__':
    unittest.main()
