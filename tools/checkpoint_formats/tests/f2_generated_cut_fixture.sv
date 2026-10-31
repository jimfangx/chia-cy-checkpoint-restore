// Real compiler-emitted reset/clock network, with the literal shell writers.
module F2GeneratedCutFixture (
    input wire clock, controller_reset, freeze_request, rst_main_n, ddr_ready,
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
    PhysicalPlanTop execution (.clock(clock), .reset(simulator_reset), .a(a), .b(b), .count(target_cycle),
        .checkpoint_physical_mask(clock_mask), .checkpoint_physical_logical_ce(logical_ce),
        .checkpoint_reset_functional(functional_reset));
    CheckpointF2ClockResetCut #(.GATES(2), .OWNERS(4)) adapter (
        .clock(clock), .controller_reset(controller_reset), .freeze_request(freeze_request),
        .rst_main_n(rst_main_n), .ddr_ready(ddr_ready), .writer_state(writer_state ^ writer_xor),
        .logical_ce(logical_ce), .target_cycle(target_cycle), .owner_present(owner_present),
        .functional_reset(functional_reset), .clock_mask(clock_mask), .read_enable(read_enable),
        .failed(failed), .captured_ce(captured_ce), .captured_writers(captured_writers),
        .cut_cycle(cut_cycle), .physical_error(physical_error), .reset_error(reset_error), .control_state(control_state));
endmodule
