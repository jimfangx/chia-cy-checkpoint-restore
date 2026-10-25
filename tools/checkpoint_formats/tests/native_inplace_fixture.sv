// In-place native-storage component. Parent control execution remains raw-clocked.
module NativeInPlaceFixture(
  input wire clock, reset, ckpt_reset, freeze_request, owner_present, write,
  input wire [1:0] enable,
  input wire [2:0] address,
  input wire [129:0] data,
  output wire [64:0] left_count, right_count,
  output wire [63:0] cycle, host_ticks_out, control_ticks_out,
  output wire [129:0] read_data,
  output wire ckpt_freeze, read_enable, physical_failed,
  output wire [1:0] logical_ce, captured_ce,
  output wire [2:0] physical_error,
  output wire [63:0] physical_cut_cycle,
  input wire [7:0] ckpt_bank,
  input wire [15:0] ckpt_slot,
  input wire [31:0] ckpt_address,
  input wire ckpt_req_valid, ckpt_resp_ready,
  output wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error, ckpt_match,
  output wire [63:0] ckpt_resp_data, ckpt_data
);
  CheckpointPhysicalClockCut #(.GATES(2),.OWNERS(1),.EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock),.reset(ckpt_reset),.freeze_request(freeze_request),.ce(logical_ce),.target_cycle(cycle),
    .owner_present(owner_present),.clock_mask(ckpt_freeze),.stopped(),.root_clock(),.gate_clock(),
    .read_enable(read_enable),.failed(physical_failed),.captured_ce(captured_ce),
    .cut_cycle(physical_cut_cycle),.error(physical_error));
  NativeHost host(.clock(clock),.reset(reset),.enable(enable),.address(address),.data(data),.write(write),
    .host_ticks_out(host_ticks_out),.control_ticks_out(control_ticks_out),.left_count(left_count),.right_count(right_count),.cycle(cycle),.read_data(read_data),
    .checkpoint_inplace_checkpoint_physical_mask(ckpt_freeze),.checkpoint_inplace_checkpoint_physical_logical_ce(logical_ce),
    .checkpoint_inplace_ckpt_freeze(ckpt_freeze),.checkpoint_inplace_ckpt_reset(ckpt_reset),
    .checkpoint_inplace_ckpt_bank(ckpt_bank),.checkpoint_inplace_ckpt_slot(ckpt_slot),.checkpoint_inplace_ckpt_address(ckpt_address),.checkpoint_inplace_ckpt_match(ckpt_match),.checkpoint_inplace_ckpt_data(ckpt_data),
    .checkpoint_inplace_ckpt_req_valid(ckpt_req_valid),.checkpoint_inplace_ckpt_req_ready(ckpt_req_ready),.checkpoint_inplace_ckpt_resp_valid(ckpt_resp_valid),
    .checkpoint_inplace_ckpt_resp_ready(ckpt_resp_ready),.checkpoint_inplace_ckpt_resp_data(ckpt_resp_data),.checkpoint_inplace_ckpt_resp_error(ckpt_resp_error));
endmodule
