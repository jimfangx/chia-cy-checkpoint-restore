// Connected native bank/CE/router plus actual FireSim Widget. Component only.
module NativeCheckpointWidgetFixture(
  input wire clock, reset,
  input wire [1:0] enable,
  input wire [2:0] address,
  input wire [129:0] data,
  input wire write,
  output wire [64:0] left_count, right_count,
  output wire [63:0] cycle,
  output wire [129:0] read_data,
  input wire awvalid, wvalid, arvalid, bready, rready,
  input wire [31:0] awaddr, araddr, wdata,
  input wire [7:0] awlen, arlen,
  input wire [2:0] awsize, arsize,
  input wire [3:0] awid, arid, strb,
  input wire wlast,
  output wire awready, wready, arready, bvalid, rvalid,
  output wire [1:0] bresp, rresp,
  output wire [3:0] bid, rid,
  output wire [31:0] rdata,
  output wire rlast,
  input wire [1:0] owner_present,
  input wire streamReady,
  output wire streamValid, streamLast, streamAbort,
  output wire [511:0] streamData,
  input wire [1:0] ce_fault,
  input wire [63:0] cycle_fault,
  output wire clock_mask, physical_stopped, physical_read_enable, physical_failed, freeze,
  output wire [1:0] logical_ce, captured_ce,
  output wire [2:0] physical_error,
  output wire [63:0] physical_cut_cycle
);
  wire controllerReset, bankValid, bankResponseReady;
  wire [31:0] entry, bank_address;
  wire [7:0] bank;
  wire [15:0] slot;
  wire descriptor_valid, bank_request_ready, bank_response_valid, bank_response_error;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth;
  wire [63:0] bank_response_data;
  NativeStorageCheckpointStateAccess access(
    .clock(clock),.reset(reset),.enable(enable),.address(address),.data(data),.write(write),
    .left_count(left_count),.right_count(right_count),.cycle(cycle),.read_data(read_data),
    .capture_reset(controllerReset),.capture_clock_mask(clock_mask),.capture_read_enable(physical_read_enable),
    .capture_captured_ce(captured_ce),.capture_logical_ce(logical_ce),
    .capture_descriptor_entry(entry),.capture_descriptor_valid(descriptor_valid),
    .capture_descriptor_bank(descriptor_bank),.capture_descriptor_slot(descriptor_slot),
    .capture_descriptor_width(descriptor_width),.capture_descriptor_depth(descriptor_depth),
    .capture_request_valid(bankValid),.capture_request_ready(bank_request_ready),
    .capture_bank(bank),.capture_slot(slot),.capture_address(bank_address),
    .capture_response_valid(bank_response_valid),.capture_response_ready(bankResponseReady),
    .capture_response_data(bank_response_data),.capture_response_error(bank_response_error));
  CheckpointCaptureWidget widget (
    .clock(clock), .reset(reset),
    .io_ctrl_aw_valid(awvalid), .io_ctrl_aw_ready(awready),
    .io_ctrl_aw_bits_addr(awaddr), .io_ctrl_aw_bits_id(awid),
    .io_ctrl_aw_bits_len(awlen), .io_ctrl_aw_bits_size(awsize),
    .io_ctrl_aw_bits_burst(2'd1), .io_ctrl_aw_bits_lock(1'b0),
    .io_ctrl_aw_bits_cache(4'd0), .io_ctrl_aw_bits_prot(3'd0),
    .io_ctrl_aw_bits_qos(4'd0), .io_ctrl_aw_bits_region(4'd0), .io_ctrl_aw_bits_user(1'b0),
    .io_ctrl_w_valid(wvalid), .io_ctrl_w_ready(wready),
    .io_ctrl_w_bits_data(wdata), .io_ctrl_w_bits_id(4'd0),
    .io_ctrl_w_bits_last(wlast), .io_ctrl_w_bits_strb(strb), .io_ctrl_w_bits_user(1'b0),
    .io_ctrl_b_valid(bvalid), .io_ctrl_b_ready(bready), .io_ctrl_b_bits_id(bid), .io_ctrl_b_bits_resp(bresp),
    .io_ctrl_ar_valid(arvalid), .io_ctrl_ar_ready(arready),
    .io_ctrl_ar_bits_addr(araddr), .io_ctrl_ar_bits_id(arid),
    .io_ctrl_ar_bits_len(arlen), .io_ctrl_ar_bits_size(arsize),
    .io_ctrl_ar_bits_burst(2'd1), .io_ctrl_ar_bits_lock(1'b0),
    .io_ctrl_ar_bits_cache(4'd0), .io_ctrl_ar_bits_prot(3'd0),
    .io_ctrl_ar_bits_qos(4'd0), .io_ctrl_ar_bits_region(4'd0), .io_ctrl_ar_bits_user(1'b0),
    .io_ctrl_r_valid(rvalid), .io_ctrl_r_ready(rready), .io_ctrl_r_bits_id(rid),
    .io_ctrl_r_bits_data(rdata), .io_ctrl_r_bits_resp(rresp), .io_ctrl_r_bits_last(rlast),
    .streamToHostCPU_ready(streamReady), .streamToHostCPU_valid(streamValid), .streamToHostCPU_bits(streamData),
    .capture_controllerReset(controllerReset), .capture_targetCycle(cycle ^ cycle_fault),
    .capture_ownerPresent(owner_present), .capture_ownerFrozen({2{freeze}}), .capture_ownerError(2'b0),
    .capture_freeze(freeze), .capture_descriptorEntry(entry), .capture_descriptorValid(descriptor_valid),
    .capture_descriptorBank(descriptor_bank), .capture_descriptorSlot(descriptor_slot),
    .capture_descriptorWidth(descriptor_width), .capture_descriptorDepth(descriptor_depth),
    .capture_bankRequestValid(bankValid), .capture_bankRequestReady(bank_request_ready),
    .capture_bank(bank), .capture_slot(slot), .capture_address(bank_address),
    .capture_bankResponseValid(bank_response_valid), .capture_bankResponseReady(bankResponseReady),
    .capture_bankResponseData(bank_response_data), .capture_bankResponseError(bank_response_error),
    .capture_streamLast(streamLast), .capture_streamAbort(streamAbort),
    .capture_physical_logicalCE(logical_ce ^ ce_fault), .capture_physical_clockMask(clock_mask),
    .capture_physical_capturedCE(captured_ce), .capture_physical_stopped(physical_stopped),
    .capture_physical_readEnable(physical_read_enable), .capture_physical_failed(physical_failed),
    .capture_physical_cutCycle(physical_cut_cycle), .capture_physical_error(physical_error)
  );
endmodule
