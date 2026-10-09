import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import FormatError, encode, decode
from tools.checkpoint_formats.tests import test_aggregate as fixture_api


class PackedAggregateTest(unittest.TestCase):
    def fixture(self, out):
        build, old, g, h, gc, hc, native, _ = fixture_api.AggregateTest().fixture(out)
        m = packed.runtime_manifest(old['profile'], g, h, old['native_owners'], old['native_build_hash'])
        build = aggregate.build_identity(m, g, h, out/'simv')
        entries = [dict(owner='generated-entry/'+e['hierarchy'],
                        width=4*((e['width']+3)//4)*e['depth'],
                        value=('001002' if e['kind']=='memory' else '1'+'0'*64)) for e in g['state']]
        data = packed.encode_aggregate(build, m, g, h, 18, entries, hc, native, 9)
        return build, m, g, h, data

    def test_wide_bits_all_addresses_and_order_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            b, m, g, h, data = self.fixture(out)
            doc = packed.prepare_aggregate_restore(data, b, m, g, h, out/'load')
            self.assertEqual(len(doc['records']), len(g['state'])+len(h['records'])+3)
            self.assertIn('emul.Top.fifo 9 2 001002\n', (out/'load').read_text())
            self.assertIn('emul.Top.counter 257 1 1'+'0'*64+'\n', (out/'load').read_text())
            self.assertEqual(packed.decode_aggregate(data, b, m, g, h), doc)
            with self.assertRaises(FormatError): aggregate.decode_aggregate(data, b, m, g, h)

    def test_every_word_padding_late_membership_schema_and_integrity_precede_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            b, m, g, h, data = self.fixture(out)
            doc = decode(data, 'fsckpt', b)
            def row(d): return next(r for r in d['records'] if r['owner'].endswith('Top.fifo'))
            variants = [data[:-1], data+b'\x00', data[:40]+bytes([data[40]^1])+data[41:]]
            for change in (lambda d:row(d).update(value='001fff'), # Final address padding.
                           lambda d:row(d).update(width=20, value='00000'),
                           lambda d:row(d).update(owner='generated-entry/Top.absent'),
                           lambda d:d['records'].pop(), lambda d:d.update(target_cycle=2**64)):
                altered = copy.deepcopy(doc); change(altered)
                altered['records'].sort(key=lambda r:r['owner'])
                variants.append(encode('fsckpt', altered))
            for bad in variants:
                path = out/'load'; path.write_text('preserve')
                with self.assertRaises(FormatError): packed.prepare_aggregate_restore(bad,b,m,g,h,path)
                self.assertEqual(path.read_text(), 'preserve')
            for change in (lambda d:d.update(generated_encoding='descending'),
                           lambda d:d.update(schema='firesim.aggregate.lowclock.v1')):
                altered=copy.deepcopy(m);change(altered)
                with self.assertRaises(FormatError): packed.decode_aggregate(data,b,altered,g,h)

    def test_bound_target_cycle_rejects_rechecksummed_wrong_counter_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            b,m,g,h,data=self.fixture(out)
            d=decode(data,'fsckpt',b)
            # Adapt the fixture's manifested wide scalar into a 64-bit counter.
            g=copy.deepcopy(g)
            entry=next(e for e in g['state'] if e['kind']=='register')
            entry['width']=64;counter=entry['hierarchy']
            m=packed.runtime_manifest(m['profile'],g,h,m['native_owners'],m['native_build_hash'],counter)
            b=aggregate.build_identity(m,g,h,out/'simv')
            d['build']=b
            r=next(r for r in d['records'] if r['owner']=='generated-entry/'+counter)
            r.update(width=64,value=f'{9:016x}')
            good=encode('fsckpt',d)
            self.assertEqual(packed.prepare_aggregate_restore(good,b,m,g,h,out/'load')['target_cycle'],9)
            for change in (lambda x:x.update(target_cycle=10),
                           lambda x:next(r for r in x['records'] if r['owner']=='generated-entry/'+counter).update(value='0000000000000008')):
                bad=copy.deepcopy(d);change(bad);(out/'load').write_text('preserve')
                with self.assertRaisesRegex(FormatError,'target cycle disagrees'):
                    packed.prepare_aggregate_restore(encode('fsckpt',bad),b,m,g,h,out/'load')
                self.assertEqual((out/'load').read_text(),'preserve')
            for owner in ('Top.absent','Top.fifo'):
                with self.assertRaises(FormatError):
                    packed.runtime_manifest(m['profile'],g,h,m['native_owners'],m['native_build_hash'],owner)
            bad=copy.deepcopy(m);bad['cut_contract']['target_cycle_semantics']='host_cycle'
            with self.assertRaises(FormatError): packed.decode_aggregate(good,b,bad,g,h)


if __name__ == '__main__': unittest.main()
