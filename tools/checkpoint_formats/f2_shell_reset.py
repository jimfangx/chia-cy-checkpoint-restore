"""Bind the literal F2 reset writers to a nondeployable verification sibling.

No Verilog parser or shell ownership inference is attempted. Only the exact
known two synchronizers and their complete named reset consumers are supported;
changed logic fails explicitly. The original shell and its AXI resets are never
rewritten. An external-source loss is cancellation, not a restorable reset.
"""
import hashlib
import re

from tools.checkpoint_formats.codec import require


INNER = """logic pre_sync_rst_n_firesim;
always_ff @(negedge rst_main_n or posedge firesim_internal_clock)
   if (!rst_main_n)
   begin
      pre_sync_rst_n_firesim  <= 0;
      rst_firesim_n_sync <= 0;
   end
   else
   begin
      pre_sync_rst_n_firesim  <= 1;
      rst_firesim_n_sync <= pre_sync_rst_n_firesim;
   end"""
DDR = """logic ddr_ready;
logic ddr_ready_pre_sync_meta, ddr_ready_sync;
always_ff @(posedge firesim_internal_clock or negedge rst_main_n) begin
   if (!rst_main_n) begin
      ddr_ready_pre_sync_meta <= 1'b0;
      ddr_ready_sync <= 1'b0;
   end else begin
      ddr_ready_pre_sync_meta <= ddr_ready;
      ddr_ready_sync <= ddr_ready_pre_sync_meta;
   end
end"""
WORDS = ['pre_sync_rst_n_firesim', 'rst_firesim_n_sync',
         'ddr_ready_pre_sync_meta', 'ddr_ready_sync']


def compact(text):
    return re.sub(r'\s+', '', re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S))


def extract(source):
    """Return original verbatim writer RTL and its fail-closed source binding."""
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    start = source.index('logic pre_sync_rst_n_firesim;')
    end = source.index('// PCIe OCL AXI-L', start)
    region = source[start:end]
    require(compact(region) == compact(INNER + DDR), 'unsupported F2 reset writer logic')
    # Remove only the known writers and declarations; all remaining uses must
    # be the three AXI reset pins and the simulator's literal reset expression.
    remainder = compact(text).replace(compact(INNER + DDR), '', 1)
    require(remainder.count('logicrst_firesim_n_sync;') == 1, 'missing shell reset declaration')
    remainder = remainder.replace('logicrst_firesim_n_sync;', '', 1)
    expected = {'.m_axi_aresetn(rst_firesim_n_sync)': 2,
                '.s_axi_aresetn(rst_firesim_n_sync)': 1,
                '.reset(!rst_firesim_n_sync||!ddr_ready_sync)': 1}
    for use, count in expected.items():
        require(remainder.count(use) == count, 'unsupported F2 reset consumer: ' + use)
        remainder = remainder.replace(use, '')
    require(not any(name in remainder for name in WORDS),
            'unowned F2 reset writer/consumer')
    require('.reset(!rst_main_n),.locked(firesim_clocking_locked)' in compact(text),
            'unsupported shell clock-generator reset')
    # Inputs/outputs retain the native names. This is independent original RTL,
    # used in both the live shell-writer fixture and the ungated reference.
    writers = ('module F2ShellResetWriters(input wire firesim_internal_clock, rst_main_n, ddr_ready_in,\n'
               'output logic rst_firesim_n_sync, output wire [3:0] writer_state, output wire simulator_reset);\n'
               + region + '\nassign ddr_ready=ddr_ready_in;\n'
               'assign writer_state={ddr_ready_sync,ddr_ready_pre_sync_meta,rst_firesim_n_sync,pre_sync_rst_n_firesim};\n'
               'assign simulator_reset=!rst_firesim_n_sync || !ddr_ready_sync;\nendmodule\n')
    return writers, dict(schema='f2-shell-reset-observation-v1',
                         shell_sha256=hashlib.sha256(source.encode()).hexdigest(),
                         writer_rtl_sha256=hashlib.sha256(writers.encode()).hexdigest(),
                         writer_bits=WORDS, external_cancellation=['rst_main_n', 'ddr_ready'],
                         unchanged_axi_reset_consumers=3, raw_clock='firesim_internal_clock',
                         clock_generator_reset='!rst_main_n', shell_modified=False,
                         shell_restore_supported=False, complete_fpga_capture=False,
                         deployable_capture_image=False)
