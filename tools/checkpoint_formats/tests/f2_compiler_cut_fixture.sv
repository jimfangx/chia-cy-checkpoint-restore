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
`ifdef CHECKPOINT_NATIVE_BANKS
    ,input wire ckpt_req_valid, ckpt_resp_ready,
    input wire [7:0] ckpt_bank,
    input wire [15:0] ckpt_slot,
    input wire [31:0] ckpt_address,
    output wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error,
    output wire [63:0] ckpt_resp_data
`endif
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
    ,input wire checkpoint_f2_shadow_request, checkpoint_f2_shadow_release,
    input wire [31:0] checkpoint_f2_shadow_word_address,
    output wire checkpoint_f2_shadow_ready, checkpoint_f2_shadow_valid, checkpoint_f2_shadow_failed,
    output wire checkpoint_f2_shadow_word_error,
    output wire [63:0] checkpoint_f2_shadow_word_data, checkpoint_f2_shadow_cut_cycle,
    output wire [5:0] checkpoint_f2_shadow_error,
    output wire [217:0] checkpoint_f2_shadow_control_state
`endif
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
        .checkpoint_f2_reset_error(reset_error), .checkpoint_f2_control_state(control_state)
`ifdef CHECKPOINT_NATIVE_BANKS
        ,.ckpt_req_valid(ckpt_req_valid), .ckpt_req_ready(ckpt_req_ready),
        .ckpt_resp_valid(ckpt_resp_valid), .ckpt_resp_ready(ckpt_resp_ready),
        .ckpt_resp_data(ckpt_resp_data), .ckpt_resp_error(ckpt_resp_error),
        .ckpt_bank(ckpt_bank), .ckpt_slot(ckpt_slot), .ckpt_address(ckpt_address)
`endif
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
        ,.checkpoint_f2_shadow_request(checkpoint_f2_shadow_request),
        .checkpoint_f2_shadow_release(checkpoint_f2_shadow_release),
        .checkpoint_f2_shadow_word_address(checkpoint_f2_shadow_word_address),
        .checkpoint_f2_shadow_ready(checkpoint_f2_shadow_ready),
        .checkpoint_f2_shadow_valid(checkpoint_f2_shadow_valid),
        .checkpoint_f2_shadow_failed(checkpoint_f2_shadow_failed),
        .checkpoint_f2_shadow_word_error(checkpoint_f2_shadow_word_error),
        .checkpoint_f2_shadow_word_data(checkpoint_f2_shadow_word_data),
        .checkpoint_f2_shadow_cut_cycle(checkpoint_f2_shadow_cut_cycle),
        .checkpoint_f2_shadow_error(checkpoint_f2_shadow_error),
        .checkpoint_f2_shadow_control_state(checkpoint_f2_shadow_control_state)
`endif
    );
endmodule
