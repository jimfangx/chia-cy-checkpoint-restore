// The adapter is instantiated and wired by the compiler INSIDE execution.
// Real compiler-emitted reset/clock network, with the literal shell writers.
module F2GeneratedCutFixture (
    input wire clock, controller_reset, freeze_request, rst_main_n, ddr_ready, raw_reset_xor,
    input wire [3:0] owner_present, writer_xor,
    output wire clock_mask, read_enable, failed, axi_reset_n, simulator_reset,
    output wire functional_reset,
    output wire [1:0] logical_ce, captured_ce, reset_error,
    output wire [2:0] physical_error,
    output wire [3:0] writer_state, captured_writers,
    output wire [63:0] target_cycle, cut_cycle,
    output wire [7:0] a,b,
    output wire [80:0] control_state
);
    F2ShellResetWriters shell (
        .firesim_internal_clock(clock), .rst_main_n(rst_main_n), .ddr_ready_in(ddr_ready),
        .rst_firesim_n_sync(axi_reset_n), .writer_state(writer_state), .simulator_reset(simulator_reset));
    PhysicalPlanTop execution (
        .clock(clock), .reset(simulator_reset ^ raw_reset_xor), .a(a), .b(b), .count(target_cycle),
        .checkpoint_physical_logical_ce(logical_ce),
        .checkpoint_f2_controller_reset(controller_reset), .checkpoint_f2_freeze_request(freeze_request),
        .checkpoint_f2_rst_main_n(rst_main_n), .checkpoint_f2_ddr_ready(ddr_ready),
        .checkpoint_f2_writer_state(writer_state ^ writer_xor), .checkpoint_f2_owner_present(owner_present),
        .checkpoint_f2_functional_reset(functional_reset), .checkpoint_f2_clock_mask(clock_mask),
        .checkpoint_f2_read_enable(read_enable), .checkpoint_f2_failed(failed),
        .checkpoint_f2_captured_ce(captured_ce), .checkpoint_f2_captured_writers(captured_writers),
        .checkpoint_f2_cut_cycle(cut_cycle), .checkpoint_f2_physical_error(physical_error),
        .checkpoint_f2_reset_error(reset_error), .checkpoint_f2_control_state(control_state));
endmodule
