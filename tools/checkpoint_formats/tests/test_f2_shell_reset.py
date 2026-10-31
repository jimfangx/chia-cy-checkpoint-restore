import unittest

from tools.checkpoint_formats.f2_shell_reset import INNER, DDR, extract


class F2ShellResetTests(unittest.TestCase):
    def source(self):
        return ('logic rst_firesim_n_sync;\n' + INNER + '\n' + DDR + '\n// PCIe OCL AXI-L\n'
                'a x(.m_axi_aresetn(rst_firesim_n_sync));\n'
                'b y(.m_axi_aresetn(rst_firesim_n_sync));\n'
                'c z(.s_axi_aresetn(rst_firesim_n_sync));\n'
                'F1Shim firesim_top(.reset(!rst_firesim_n_sync || !ddr_ready_sync));\n'
                'clk_wiz_0_firesim pll(.reset(!rst_main_n),.locked(firesim_clocking_locked));\n')

    def test_verbatim_writers_and_explicit_external_boundary(self):
        source = self.source()
        rtl, binding = extract(source)
        self.assertIn(INNER, rtl)
        self.assertIn(DDR, rtl)
        self.assertEqual(binding['unchanged_axi_reset_consumers'], 3)
        self.assertEqual(binding['external_cancellation'], ['rst_main_n', 'ddr_ready'])
        self.assertFalse(binding['shell_restore_supported'])
        self.assertFalse(binding['deployable_capture_image'])
        self.assertEqual(len(binding['writer_bits']), 4)

    def test_changed_writer_semantics_reject(self):
        for before, after in [('negedge rst_main_n', 'posedge rst_main_n'),
                              ('ddr_ready_sync <= ddr_ready_pre_sync_meta', 'ddr_ready_sync <= ddr_ready'),
                              ('posedge firesim_internal_clock', 'posedge another_clock'),
                              ('pre_sync_rst_n_firesim  <= 1', 'pre_sync_rst_n_firesim <= 0')]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                extract(self.source().replace(before, after, 1))

    def test_extra_unowned_consumer_and_writer_reject(self):
        for extra in ['assign extra=ddr_ready_sync;',
                      'always @(posedge other) rst_firesim_n_sync <= 1;',
                      'wire unused_pre_sync_rst_n_firesim;',
                      'assign ddr_ready_pre_sync_meta=0;']:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                extract(self.source() + extra)

    def test_missing_axi_or_clock_reset_reject(self):
        for before, after in [('.s_axi_aresetn(rst_firesim_n_sync)', '.s_axi_aresetn(held_reset_n)'),
                              ('.reset(!rst_main_n)', '.reset(held_reset)'),
                              ('!rst_firesim_n_sync || !ddr_ready_sync', '!ddr_ready_sync')]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                extract(self.source().replace(before, after))

    def test_cosmetic_change_retains_distinct_source_provenance(self):
        _, original = extract(self.source())
        rtl, changed = extract(self.source().replace('ddr_ready_sync <=', 'ddr_ready_sync  /* unchanged */ <=', 1))
        self.assertNotEqual(original['shell_sha256'], changed['shell_sha256'])
        self.assertNotEqual(original['writer_rtl_sha256'], changed['writer_rtl_sha256'])
        self.assertIn('/* unchanged */', rtl)
