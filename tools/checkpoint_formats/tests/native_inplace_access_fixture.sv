// In-place native-storage component. Parent control execution remains raw-clocked.
module NativeInPlaceAccessFixture(
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
  output wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error,
  input wire [31:0] descriptor_entry,
  output wire descriptor_valid,
  output wire [7:0] descriptor_bank,
  output wire [15:0] descriptor_slot, descriptor_width,
  output wire [31:0] descriptor_depth,
  output wire [63:0] ckpt_resp_data
);
  CheckpointPhysicalClockCut #(.GATES(2),.OWNERS(1),.EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock),.reset(ckpt_reset),.freeze_request(freeze_request),.ce(logical_ce),.target_cycle(cycle),
    .owner_present(owner_present),.clock_mask(ckpt_freeze),.stopped(),.root_clock(),.gate_clock(),
    .read_enable(read_enable),.failed(physical_failed),.captured_ce(captured_ce),
    .cut_cycle(physical_cut_cycle),.error(physical_error));
  NativeHostCheckpointStateAccess host(.clock(clock),.reset(reset),.enable(enable),.address(address),.data(data),.write(write),
    .host_ticks_out(host_ticks_out),.control_ticks_out(control_ticks_out),.left_count(left_count),.right_count(right_count),.cycle(cycle),.read_data(read_data),
    .capture_clock_mask(ckpt_freeze),.capture_logical_ce(logical_ce),
    .capture_reset(ckpt_reset),.capture_read_enable(read_enable),.capture_captured_ce(captured_ce),
    .capture_descriptor_entry(descriptor_entry),.capture_descriptor_valid(descriptor_valid),
    .capture_descriptor_bank(descriptor_bank),.capture_descriptor_slot(descriptor_slot),
    .capture_descriptor_width(descriptor_width),.capture_descriptor_depth(descriptor_depth),
    .capture_bank(ckpt_bank),.capture_slot(ckpt_slot),.capture_address(ckpt_address),
    .capture_request_valid(ckpt_req_valid),.capture_request_ready(ckpt_req_ready),
    .capture_response_valid(ckpt_resp_valid),.capture_response_ready(ckpt_resp_ready),
    .capture_response_data(ckpt_resp_data),.capture_response_error(ckpt_resp_error));
endmodule
