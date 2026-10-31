module ResetCutWiringFixture(
  input wire clock, controller_reset, freeze_request, reset_writer_present,
  input wire reset_in,
  input wire [2:0] owner_present,
  output wire [7:0] a,b,
  output wire [63:0] count,cut_cycle,
  output wire clock_mask,stopped,read_enable,failed,functional_reset,
  output wire [1:0] captured_ce,
  output wire [2:0] physical_error,
  output wire [1:0] reset_error
);
  wire [1:0] logical_ce;
  wire captured_reset;
  PhysicalPlanTop execution(.clock(clock),.reset(reset_in),.a(a),.b(b),.count(count),
    .checkpoint_physical_mask(clock_mask),.checkpoint_physical_logical_ce(logical_ce),
    .checkpoint_reset_functional(functional_reset));
  CheckpointResetOwnedClockCut #(.GATES(2),.OWNERS(3),.RESETS(1),.EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock),.controller_reset(controller_reset),.freeze_request(freeze_request),
    .ce(logical_ce),.target_cycle(count),.owner_present(owner_present),
    .reset_writer_present(reset_writer_present),.reset_in(reset_in),
    .functional_reset(functional_reset),.clock_mask(clock_mask),.stopped(stopped),
    .read_enable(read_enable),.failed(failed),.captured_ce(captured_ce),.cut_cycle(cut_cycle),
    .physical_error(physical_error),.reset_error(reset_error),.captured_reset(captured_reset));
endmodule
