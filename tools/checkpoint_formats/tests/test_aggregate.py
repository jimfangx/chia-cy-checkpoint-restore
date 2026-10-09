import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.aggregate import (runtime_manifest, build_identity, encode_aggregate,
    decode_aggregate, prepare_aggregate_restore)
from tools.checkpoint_formats.codec import FormatError, decode, encode
from tools.checkpoint_formats.harness_restore import harness_layout, harness_capture
from tools.checkpoint_formats.simulator import generated_capture, generated_words
from tools.checkpoint_formats.tests.test_simulator import fixture
from tools.checkpoint_formats.tests.test_harness_restore import TOP, CONSTANTS


class AggregateTest(unittest.TestCase):
    def fixture(self, out):
        g = fixture()
        layout = harness_layout(TOP.read_text(), CONSTANTS, '', 'a'*64)
        owners = [dict(owner='runtime/mmio', schema='firesim.mmio.full.v1'),
                  dict(owner='runtime/memory', schema='firesim.mm_magic.full.v1')]
        manifest = runtime_manifest('test-only-profile', g, layout, owners, 'b'*64)
        executable = out/'simv'; executable.write_bytes(b'test-executable')
        build = build_identity(manifest, g, layout, executable)
        gc = generated_capture(g, ['0'*((w['width']+3)//4) for w in generated_words(g)], 18)
        hc = harness_capture(layout, ['0'*((r['width']+3)//4) for r in layout['records']], 18)
        native = {'runtime/mmio': b'\x00\x12\xff', 'runtime/memory': bytes(range(256))}
        data = encode_aggregate(build, manifest, g, layout, gc, hc, native, 9)
        return build, manifest, g, layout, gc, hc, native, data

    def test_bound_complete_aggregate_preserves_opaque_bytes_and_target_time(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            build, m, g, h, gc, hc, native, data = self.fixture(out)
            self.assertEqual(data, encode_aggregate(build, m, g, h, gc, hc, native, 9))
            doc = prepare_aggregate_restore(data, build, m, g, h, out/'load')
            self.assertEqual(doc['target_cycle'], 9)
            self.assertIn(' 9 18 2\n', (out/'load').read_text())
            self.assertIn('HOST runtime/mmio firesim.mmio.full.v1 3 0012ff\n', (out/'load').read_text())
            self.assertEqual(decode_aggregate(data, build, m, g, h), doc)

    def test_checksums_build_membership_shapes_and_flags_reject_without_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            build, m, g, h, gc, hc, native, data = self.fixture(out)
            doc = decode(data, 'fsckpt', build)
            def row(d, owner): return next(r for r in d['records'] if r['owner']==owner)
            changes = [lambda d:d['records'].pop(),
                       lambda d:d.update(target_cycle=2**64),
                       lambda d:row(d,'host/runtime/mmio').update(owner='host/unsupported'),
                       lambda d:row(d,'host/runtime/mmio').update(width=23,value='0012ff'),
                       lambda d:row(d,'harness/emul.fin').update(value='1'),
                       lambda d:row(d,'harness/emul.reset').update(value='1'),
                       lambda d:row(d,'cut/host_sample').update(width=32,value='00000012'),
                       lambda d:row(d,'generated/Top.counter').update(width=256,value='0'*64)]
            bad = [data[:-1], data+b'\x00', data[:30]+bytes([data[30]^1])+data[31:]]
            for change in changes:
                changed = copy.deepcopy(doc); change(changed)
                bad.append(encode('fsckpt',changed)) # Recomputed checksums must not bypass semantic checks.
            for invalid in bad:
                for sentinel in (None, 'preserve'):
                    path=out/'load'
                    if sentinel is None: path.unlink(missing_ok=True)
                    else: path.write_text(sentinel)
                    with self.assertRaises(FormatError): prepare_aggregate_restore(invalid,build,m,g,h,path)
                    self.assertEqual(path.read_text() if path.exists() else None,sentinel)
            for key in build:
                changed=dict(build); changed[key]='0'*64
                with self.assertRaises(FormatError): decode_aggregate(data,changed,m,g,h)
            for change in (lambda d:d.update(phase='posedge'),
                           lambda d:d['native_owners'][-1].update(schema='unsupported'),
                           lambda d:d.update(native_build_hash='c'*64),
                           lambda d:d.update(generated_manifest_hash='c'*64)):
                changed=copy.deepcopy(m);change(changed)
                with self.assertRaises(FormatError): decode_aggregate(data,build,changed,g,h)

    def test_incoherent_cut_and_unsupported_native_inventory_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            build, m, g, h, gc, hc, native, data = self.fixture(out)
            hc['host_sample'] += 1
            with self.assertRaises(FormatError): encode_aggregate(build,m,g,h,gc,hc,native,9)
            for owners in ([], [dict(owner='runtime/a',schema='')],
                           [dict(owner='runtime/a',schema='v1')]*2,
                           [dict(owner='runtime/a\nescape',schema='v1')]):
                with self.assertRaises(FormatError): runtime_manifest('test',g,h,owners,'b'*64)
            hc['host_sample'] -= 1
            for changed in ({},dict(native,extra=b'\x00'),dict(native,**{'runtime/mmio':b''})):
                with self.assertRaises(FormatError): encode_aggregate(build,m,g,h,gc,hc,changed,9)


if __name__=='__main__': unittest.main()
