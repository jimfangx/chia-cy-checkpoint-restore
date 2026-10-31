module F2ResetGuardFixture (
    input wire clock, controller_reset, freeze_request, rst_main_n, ddr_ready,
    input wire [3:0] owner_present, writer_xor,
    output wire root_clock, clock_mask, read_enable, failed,
    output wire [2:0] gate_clock, ce, physical_error,
    output wire [3:0] writer_state, captured_writers,
    output wire axi_reset_n, simulator_reset, functional_reset,
    output wire [63:0] target_cycle, cut_cycle,
    output wire [95:0] functional_words,
    output wire [81:0] control_state
);
    wire writer_present, guard_failed;
    wire [5:0] guard_state;
    wire [75:0] cut_state;
    wire core_failed;
    F2ShellResetWriters shell (
        .firesim_internal_clock(clock), .rst_main_n(rst_main_n), .ddr_ready_in(ddr_ready),
        .rst_firesim_n_sync(axi_reset_n), .writer_state(writer_state), .simulator_reset(simulator_reset));
    CheckpointF2ResetGuard guard (
        .clock(clock), .controller_reset(controller_reset), .clock_mask(clock_mask),
        .rst_main_n(rst_main_n), .ddr_ready(ddr_ready), .writer_state(writer_state ^ writer_xor),
        .writer_present(writer_present), .failed(guard_failed), .captured_writers(captured_writers),
        .control_state(guard_state));
    CheckpointResetOwnedClockCut #(.GATES(3), .OWNERS(4), .RESETS(1)) cut (
        .clock(clock), .controller_reset(controller_reset),
        .freeze_request(freeze_request || (clock_mask && guard_failed)),
        .ce(ce), .target_cycle(target_cycle), .owner_present(owner_present),
        .reset_writer_present(writer_present), .reset_in(simulator_reset),
        .functional_reset(functional_reset), .root_clock(root_clock), .gate_clock(gate_clock),
        .clock_mask(clock_mask), .read_enable(read_enable), .failed(core_failed),
        .cut_cycle(cut_cycle), .physical_error(physical_error), .control_state(cut_state));
    assign failed = core_failed || guard_failed;
    assign control_state = {guard_state, cut_state};
    reg [63:0] cycle_count;
    reg [31:0] state0, state1, state2;
    assign target_cycle = cycle_count;
    assign functional_words = {state2,state1,state0};
    assign ce = functional_reset ? 3'b111 : {cycle_count[1]^cycle_count[0],cycle_count[2],!cycle_count[0]};
    always @(posedge root_clock)
        if(functional_reset) cycle_count<=0; else cycle_count<=cycle_count+1;
    always @(posedge gate_clock[0])
        if(functional_reset) state0<=1; else state0<=(state0*33)^cycle_count[31:0];
    always @(posedge gate_clock[1])
        if(functional_reset) state1<=2; else state1<=(state1*33)^(cycle_count[31:0]+1);
    always @(posedge gate_clock[2])
        if(functional_reset) state2<=3; else state2<=(state2*33)^(cycle_count[31:0]+2);
endmodule
