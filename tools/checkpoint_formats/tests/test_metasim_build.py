"""Generated constructor coverage and fail-closed topology for normal Make."""
import unittest
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.metasim_build import WIDGETS, native_inventory
from tools.checkpoint_formats.tests.verify_production_aggregate_vcs import prepare_output


class MakeInventoryTest(unittest.TestCase):
    def test_repeat_preserves_executable_companions_and_prior_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(prepare_output(root, True), root)
            image = root/'AXI4Fuzzer-checkpoint'; image.write_bytes(b'executable')
            (root/'simv').symlink_to(image.name)
            companions = root/'AXI4Fuzzer-checkpoint.daidir'; companions.mkdir()
            (companions/'archive.so').write_bytes(b'loaded library')
            (root/'capture.fsckpt').write_bytes(b'checkpoint')
            (root/'capture.log').write_bytes(b'evidence')
            before = {p: (p.lstat().st_ino, p.read_bytes()) for p in root.rglob('*') if p.is_file()}
            first, second = prepare_output(root, True), prepare_output(root, True)
            self.assertNotEqual(first, second)
            self.assertEqual(first.parent, root)
            self.assertEqual(list(first.iterdir()), [])
            self.assertEqual(before, {p: (p.lstat().st_ino, p.read_bytes()) for p in before})

    def header(self):
        return ''.join('#ifdef '+('GET_CORE_CONSTRUCTOR' if kind in ('master_t', 'loadmem_t')
                                 else 'GET_BRIDGE_CONSTRUCTOR')+'\n'
                       'registry.add_widget(new '+kind+'(simif, args));\n#endif\n'
                       for kind in WIDGETS)

    def constants(self):
        return ''.join(f'`define MEM_HAS_CHANNEL{i} 1\n' for i in range(4))

    def test_constructor_pass_order_and_complete_native_inventory(self):
        # Golden Gate interleaves the loadmem core constructor after bridges;
        # entry instantiates all core constructors before any bridge.
        header = self.header()
        start = header.index('#ifdef GET_CORE_CONSTRUCTOR', 1)
        stop = header.index('#endif\n', start)+len('#endif\n')
        header = header[:start]+header[stop:]+header[start:stop]
        rows = native_inventory(header, self.constants())
        self.assertEqual(len(rows), 17)
        self.assertEqual(rows[6:12], [dict(owner=f'widget/{i}', schema=schema)
                                     for i, schema in enumerate(WIDGETS.values())])
        self.assertEqual([r['owner'] for r in rows[1:5]],
                         [f'runtime/functional-memory/{i}' for i in range(4)])

    def test_unregistered_changed_or_nested_constructors_reject(self):
        good = self.header()
        invalid = [good.replace('master_t', 'uart_t'), good+good,
                   good.replace('new master_t(', 'new master_t(new Other(), '),
                   good.replace('registry.add_widget', 'registry.other', 1),
                   good.replace('GET_CORE_CONSTRUCTOR', 'GET_UNKNOWN_CONSTRUCTOR', 1),
                   good.replace('new master_t', 'new loadmem_t', 1)]
        # Swapping bridge constructors changes widget IDs even if all schemas
        # are supported individually.
        invalid.append(good.replace('clockmodule_t', 'TEMP').replace('reset_pulse_t',
                       'clockmodule_t').replace('TEMP', 'reset_pulse_t'))
        for header in invalid:
            with self.subTest(header=header), self.assertRaises(FormatError):
                native_inventory(header, self.constants())

    def test_missing_extra_duplicate_and_stream_channels_reject(self):
        good = self.constants()
        invalid = [good.replace('`define MEM_HAS_CHANNEL3 1\n', ''),
                   good+'`define MEM_HAS_CHANNEL4 1\n',
                   good+'`define MEM_HAS_CHANNEL0 1\n']
        invalid += [good+'`define '+m+' 1\n' for m in
                    ('QSFP_HAS_CHANNEL0', 'CPU_MANAGED_AXI4_PRESENT', 'FPGA_MANAGED_AXI4_PRESENT')]
        for constants in invalid:
            with self.subTest(constants=constants), self.assertRaises(FormatError):
                native_inventory(self.header(), constants)


if __name__ == '__main__':
    unittest.main()
