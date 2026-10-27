// Component wrapper: two existing executions, one raw transport and low-phase cut.
// The sole fixture owner is explicit; this is not production owner coverage.
module NativeRegionsFixture(
  input wire clock, reset, capture_reset, freeze_request, owner_present, write,
  input wire [1:0] enable,
  input wire [2:0] address,
  input wire [129:0] data,
  output wire [64:0] left_count, right_count, other_left_count, other_right_count,
  output wire [63:0] cycle, other_cycle, host_ticks_out, control_ticks_out,
  output wire [129:0] read_data, other_read_data,
  output wire capture_clock_mask, capture_read_enable, failed,
  output wire [3:0] capture_logical_ce, capture_captured_ce,
  output wire [2:0] error,
  output wire [63:0] cut_cycle,
  input wire [31:0] capture_descriptor_entry,
  output wire capture_descriptor_valid,
  output wire [7:0] capture_descriptor_bank,
  output wire [15:0] capture_descriptor_slot, capture_descriptor_width,
  output wire [31:0] capture_descriptor_depth,
  input wire capture_request_valid,
  output wire capture_request_ready,
  input wire [7:0] capture_bank,
  input wire [15:0] capture_slot,
  input wire [31:0] capture_address,
  output wire capture_response_valid,
  input wire capture_response_ready,
  output wire [63:0] capture_response_data,
  output wire capture_response_error
);
  CheckpointPhysicalClockCut #(.GATES(4), .OWNERS(1), .EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock), .reset(capture_reset), .freeze_request(freeze_request),
    .ce(capture_logical_ce), .target_cycle(cycle), .owner_present(owner_present),
    .clock_mask(capture_clock_mask), .stopped(), .root_clock(), .gate_clock(),
    .read_enable(capture_read_enable), .failed(failed), .captured_ce(capture_captured_ce),
    .cut_cycle(cut_cycle), .error(error));
  NativeHost host(.*);
endmodule
