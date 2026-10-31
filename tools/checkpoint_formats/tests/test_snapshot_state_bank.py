"""Native-owner streams must bind complete controls, selectors and payload."""
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.fpga_transport import crc32c
from tools.checkpoint_formats.tests.verify_snapshot_state_bank import SOURCES, audit_frames, sha, tcl, validate_inputs


class SnapshotStateBankTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"cut.frames"
        self.bits, self.cut = 130, 37
        self.payload = (1 << 129) | 0x123456789
        # Separate native staging, physical cut and sequencer owner state.
        staging = self.payload | 1 << 130 | self.cut << 131
        physical = 3 | 5 << 3 | self.cut << 6
        owner = staging | physical << 201 | 3 << 274
        control_words, payload_words = 5, 3
        words = [0x123456789abcdef0] + [(owner >> (64*i)) & ((1 << 64)-1) for i in range(control_words)]
        words += [(self.payload >> (64*i)) & ((1 << 64)-1) for i in range(payload_words)]
        base = 0x3154504b434d5346 | 1 << 64 | self.cut << 96
        self.frames = [base | 1 << 80 | 4 << 224 | int("0123456789abcdef"*4,16) << 256]
        for i, word in enumerate(words):
            if i == 0: ordinal, address, width, bank, slot = 0, 0, 64, 1, 0
            elif i <= 5: ordinal, address, width, bank, slot = 1, i-1, 64, 251, 0
            elif i <= 7: ordinal, address, width, bank, slot = 2, i-6, 64, 252, 0
            else: ordinal, address, width, bank, slot = 3, 0, 2, 252, 1
            descriptor = ordinal << 224 | address << 256 | width << 288 | bank << 304 | slot << 312
            self.frames.append(base | 2 << 80 | i << 160 | descriptor | word << 336)
        self.frames.append(base | 3 << 80 | len(words) << 160)
        self.save()

    def save(self, recheck=True):
        if recheck:
            raw = b"".join(f.to_bytes(64,"little") for f in self.frames[:-1])
            self.frames[-1] &= ~(((1 << 32)-1) << 224)
            self.frames[-1] |= (crc32c(raw)^0xffffffff) << 224
        self.path.write_text("".join(f"{f:0128x}\n" for f in self.frames))

    def test_complete_native_owner(self):
        row = audit_frames(self.path,self.bits)
        self.assertEqual((row['cut'],row['owner_bits'],row['frames']),(37,283,11))

    def test_truncated_and_duplicated_words(self):
        for index in (0,1,5,9):
            with self.subTest(index=index):
                original=self.frames.copy()
                del self.frames[index]
                self.save(False)
                with self.assertRaises(FormatError):audit_frames(self.path,self.bits)
                self.frames=original
        self.frames[2]=self.frames[1]
        self.save()
        with self.assertRaisesRegex(FormatError,'duplicate DMA word'):audit_frames(self.path,self.bits)

    def test_corrupt_crc(self):
        self.frames[1] ^= 1 << 336
        self.save(False)
        with self.assertRaisesRegex(FormatError,'bad DMA CRC'):audit_frames(self.path,self.bits)

    def test_nonzero_trailer_reserved_bits(self):
        self.frames[-1] ^= 1 << 256
        self.save(False)
        with self.assertRaisesRegex(FormatError,'trailer reserved bits'):audit_frames(self.path,self.bits)

    def test_rechecksummed_selector_and_cycle_corruption(self):
        for index,bit in ((1,304),(2,256),(1,96)):
            with self.subTest(index=index,bit=bit):
                original=self.frames.copy()
                self.frames[index] ^= 1 << bit
                self.save()
                with self.assertRaises(FormatError):audit_frames(self.path,self.bits)
                self.frames=original

    def test_rechecksummed_missing_control_bits(self):
        for bit in (130,131,195,201,202,203,207,271,274,277):
            with self.subTest(bit=bit):
                original=self.frames.copy()
                self.frames[2+bit//64] ^= 1 << (336+bit%64)
                self.save()
                with self.assertRaises(FormatError):audit_frames(self.path,self.bits)
                self.frames=original

    def test_rechecksummed_padding_and_payload_corruption(self):
        for index,bit in ((6,40),(9,40),(2,0),(7,0)):
            with self.subTest(index=index,bit=bit):
                original=self.frames.copy()
                self.frames[index] ^= 1 << (336+bit)
                self.save()
                with self.assertRaises(FormatError):audit_frames(self.path,self.bits)
                self.frames=original


class FrozenSnapshotInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.sources={}
        for name in SOURCES:
            path=self.root/'sources'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('bound-source:'+name)
            self.sources[name]=sha(path)
        (self.root/'native.tcl').write_text(tcl())
        self.inputs={'sources/'+n:h for n,h in self.sources.items()}
        self.inputs['native.tcl']=sha(self.root/'native.tcl')

    def test_complete_frozen_namespace(self):
        validate_inputs(self.root,self.inputs,self.sources)

    def test_coherently_rehashed_stale_sources_reject(self):
        for name in SOURCES:
            with self.subTest(name=name):
                path=self.root/'sources'/name
                original=path.read_bytes();path.write_text('stale')
                inputs=dict(self.inputs,**{'sources/'+name:sha(path)})
                with self.assertRaisesRegex(FormatError,'input table differs'):
                    validate_inputs(self.root,inputs,self.sources)
                path.write_bytes(original)

    def test_missing_input_rejects(self):
        for name in self.inputs:
            inputs=dict(self.inputs);del inputs[name]
            with self.subTest(name=name),self.assertRaises(FormatError):
                validate_inputs(self.root,inputs,self.sources)

    def test_extra_input_rejects(self):
        inputs=dict(self.inputs,unexpected='0'*64)
        with self.assertRaises(FormatError):validate_inputs(self.root,inputs,self.sources)

    def test_changed_or_missing_frozen_source_rejects(self):
        path=self.root/'sources'/SOURCES[0]
        path.write_text('changed')
        with self.assertRaises(FormatError):validate_inputs(self.root,self.inputs,self.sources)
        path.unlink()
        with self.assertRaises(FormatError):validate_inputs(self.root,self.inputs,self.sources)

    def test_coherently_rehashed_tcl_rejects(self):
        path=self.root/'native.tcl';path.write_text(tcl()+'\n# unbound edit\n')
        inputs=dict(self.inputs,**{'native.tcl':sha(path)})
        with self.assertRaisesRegex(FormatError,'input table differs'):
            validate_inputs(self.root,inputs,self.sources)

    def test_incomplete_source_namespace_rejects(self):
        sources=dict(self.sources);del sources[SOURCES[0]]
        with self.assertRaisesRegex(FormatError,'source namespace'):
            validate_inputs(self.root,self.inputs,sources)

    def test_symlinked_frozen_input_rejects(self):
        path=self.root/'sources'/SOURCES[0];data=path.read_bytes();path.unlink()
        other=self.root/'other';other.write_bytes(data);path.symlink_to(other)
        with self.assertRaises(FormatError):validate_inputs(self.root,self.inputs,self.sources)

