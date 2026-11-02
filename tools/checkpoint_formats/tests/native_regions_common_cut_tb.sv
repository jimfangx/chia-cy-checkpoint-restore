`timescale 1ns/1ps
// All data expectations use independent arithmetic/memory, never state backdoors.
module native_regions_common_cut_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=!clock;
  reg reset=1, capture_reset=1, freeze_request=0, owner_present=1, write=0;
  // Explicit test-only perturbation of the collector input, never functional state.
  reg [63:0] cut_cycle_xor=0;
  reg [1:0] enable=3;
  reg [2:0] address=0;
  reg [129:0] data=0;
  wire [64:0] left_count, right_count, other_left_count, other_right_count;
  wire [63:0] cycle, other_cycle, host_ticks_out, control_ticks_out;
  wire [129:0] read_data, other_read_data;
  wire capture_clock_mask, capture_read_enable, failed;
  wire [3:0] capture_logical_ce, capture_captured_ce;
  wire [2:0] error;
  wire [63:0] cut_cycle;
  reg [31:0] capture_descriptor_entry=0;
  wire capture_descriptor_valid;
  wire [7:0] capture_descriptor_bank;
  wire [15:0] capture_descriptor_slot, capture_descriptor_width;
  wire [31:0] capture_descriptor_depth;
  reg capture_request_valid=0, capture_response_ready=0;
  wire capture_request_ready, capture_response_valid, capture_response_error;
  reg [7:0] capture_bank=0;
  reg [15:0] capture_slot=0;
  reg [31:0] capture_address=0;
  wire [63:0] capture_response_data;
  NativeRegionsFixture dut(.*);
  reg [64:0] expected_left=0, expected_right=0, expected_other_left=0, expected_other_right=0;
  reg [63:0] expected_cycle=0, expected_raw=0;
  reg [129:0] memory[0:7], other_memory[0:7], expected_read, expected_other_read;
  reg [3:0] expected_ce;
  bit armed=0, missing_owner, ce_drift, cycle_drift;
  bit pending_owner, pending_ce, pending_cycle, release_owner, release_ce, release_cycle;
  integer requests=0, responses=0, withdrawal_stalls=0, gate_edges=0;
  string rejection_kind;
  always @(posedge clock) begin
    if(!capture_reset) begin
      if(capture_request_valid && capture_request_ready) requests++;
      if(capture_response_valid && capture_response_ready) responses++;
    end
  end
  // The bank hold mux can hide a broken clock mask. Observe the six actual
  // generated primitive outputs as well as independently checking functional data.
  always @(posedge dut.host.stage.network.checkpoint_physical_root_gate.O or
           posedge dut.host.stage.network.left_.gate.O or
           posedge dut.host.stage.network.right_.gate.O or
           posedge dut.host.stage.peer.checkpoint_physical_root_gate.O or
           posedge dut.host.stage.peer.left_.gate.O or
           posedge dut.host.stage.peer.right_.gate.O) begin
    if(armed) begin
      gate_edges++;
      check(!capture_clock_mask,"no physical region clock edge while common mask is held");
    end
  end
  integer checks=0, words=0, stalls=0, cuts=0;
  task check(input bit ok, input string why);
    checks++;
    if(!ok) begin
      $display("NATIVE_REGIONS_DIVERGENCE reason=%s cut=%0d cycle=%0d word=%0d response_ack=%0b checks=%0d",why,cuts,expected_cycle,words,capture_response_ready,checks);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  always @(posedge clock) begin
    if(reset) expected_raw=0; else expected_raw++;
    if(!capture_clock_mask) begin
      if(reset) begin
        expected_cycle=0;
        if(enable[0]) expected_left=0; else expected_other_left=0;
        if(enable[1]) expected_right=0; else expected_other_right=0;
      end else begin
        expected_cycle++;
        if(enable[0]) expected_left++; else expected_other_left++;
        if(enable[1]) expected_right++; else expected_other_right++;
      end
      expected_read=memory[address]; expected_other_read=other_memory[address];
      if(write) begin memory[address]=data; other_memory[address]=data ^ {2'b10,64'd0,64'h123456789abcdef0}; end
    end
    #1;
    if(armed) begin
      check(cycle===expected_cycle && other_cycle===expected_cycle,"both independent target counters");
      check({left_count,right_count,other_left_count,other_right_count}===
        {expected_left,expected_right,expected_other_left,expected_other_right},"independent enabled counters in both regions");
      check(read_data===expected_read && other_read_data===expected_other_read,"distinct old-read memory pipelines");
      check(host_ticks_out===expected_raw && control_ticks_out===expected_raw,"shared ancestor control remains raw");
    end
  end
  task readword(input integer bank, input integer slot, input integer at, input reg [63:0] expected, input bit err);
    @(negedge clock); #1;
    capture_bank=bank; capture_slot=slot; capture_address=at; capture_request_valid=1; capture_response_ready=0;
    #1; check(capture_request_ready,"shared raw request ready");
    @(posedge clock); #2; capture_request_valid=0;
    for(integer k=0; !capture_response_valid && k<12; k++) begin @(posedge clock); #2; end
    check(capture_response_valid && capture_response_error===err && capture_response_data===expected,"exact selected regional word/error");
    for(integer k=0;k<3;k++) begin
      @(negedge clock); #1; capture_bank=254; capture_slot=65535; capture_address=32'hffffffff;
      @(posedge clock); #2; stalls++;
      check(capture_response_valid && !capture_request_ready && capture_response_data===expected && capture_response_error===err,"owner pinned through backpressure");
    end
    @(negedge clock); #1; capture_response_ready=1;
    @(posedge clock); #2; capture_response_ready=0; words++;
    check(!capture_response_valid,"response drained");
  endtask
  `include "native-regions-selectors.svh"
  task active(input integer count);
    for(integer k=0;k<count;k++) begin
      @(negedge clock); #1;
      enable=k%4; address=k%8; write=1;
      data={2'(k%4),64'hfedcba9876543210 ^ 64'(k),64'h1020304050607080 ^ (64'(k)*64'h1234567)};
    end
    @(negedge clock); #1; write=0; enable=1;
  endtask
  task begin_cut;
    @(posedge clock); #2; expected_ce={~enable,enable}; freeze_request=1;
    @(negedge clock); #1; check(capture_clock_mask,"one common low-phase mask");
    @(posedge clock); #2; cuts++;
  endtask
  task begin_pending;
    @(negedge clock); #1;
    capture_bank=255; capture_slot=0; capture_address=0;
    capture_request_valid=1; capture_response_ready=0;
    #1; check(capture_request_ready,"pending-read request accepted only at valid cut");
    @(posedge clock); #2; capture_request_valid=0;
    for(integer k=0; !capture_response_valid && k<12; k++) begin @(posedge clock); #2; end
    check(capture_response_valid && !capture_response_error &&
      capture_response_data===64'(expected_ce[0]),"real physical CE response outstanding");
  endtask
  task inject_fault(input integer kind);
    if(kind==0) owner_present=0;
    else if(kind==1) enable=~enable;
    else cut_cycle_xor=64'd1;
  endtask
  task reject_fault(input integer kind, input string label);
    integer before_acks, before_requests;
    before_acks=responses; before_requests=requests;
    // These are combinational cancellation checks before the next raw edge.
    #1;
    check(failed && !capture_read_enable && !capture_request_ready && !capture_response_valid &&
      capture_clock_mask,"fault immediately revokes both handshakes and holds cut");
    capture_request_valid=1; capture_response_ready=1;
    repeat(3) begin @(posedge clock); #2; end
    check(responses==before_acks && requests==before_requests,"faulted beat never acknowledged or replaced");
    check(error[kind] && failed && capture_clock_mask,"correct sticky physical error owner");
    @(negedge clock); #1;
    owner_present=1; enable=1; cut_cycle_xor=0; freeze_request=0;
    repeat(4) begin @(posedge clock); #2; end
    check(failed && capture_clock_mask && !capture_read_enable && !capture_request_ready &&
      !capture_response_valid && responses==before_acks && requests==before_requests,
      "source return and host withdrawal cannot repair cancelled cut");
    $display("NATIVE_REGIONS_REJECTED kind=%s checks=%0d requests=%0d responses=%0d",label,checks,requests,responses);
    $finish;
  endtask
  task withdrawal;
    integer before_acks, before_requests;
    begin_pending(); before_acks=responses; before_requests=requests;
    @(negedge clock); #1; freeze_request=0;
    capture_request_valid=1; capture_bank=254; capture_slot=65535; capture_address=32'hffffffff;
    repeat(16) begin
      @(posedge clock); #2; withdrawal_stalls++;
      check(capture_clock_mask && capture_read_enable && !failed && !capture_request_ready &&
        capture_response_valid && capture_response_data===64'(expected_ce[0]) && !capture_response_error,
        "withdrawal retains original response and common stop through long backpressure");
      check(requests==before_requests && responses==before_acks,"withdrawal permits no new request or premature acknowledgement");
    end
    @(negedge clock); #1; capture_response_ready=1;
    @(posedge clock); #2; capture_response_ready=0; capture_request_valid=0;
    check(responses==before_acks+1 && requests==before_requests && !capture_response_valid && capture_clock_mask,
      "one accepted response drains before any functional clock release");
    @(negedge clock); #1; check(capture_clock_mask,"cut retained until registered release decision");
    @(posedge clock); #2; check(capture_clock_mask,"release decision uses one complete raw control edge");
    @(negedge clock); #1; check(!capture_clock_mask && !failed,"common mask releases on following low phase");
  endtask
  task capture;
    begin_cut();
    if(missing_owner) reject_fault(0,"missing-owner");
    check(capture_read_enable && !failed && cut_cycle==expected_cycle,"common cut valid and cycle labelled");
    check(capture_captured_ce===expected_ce && capture_logical_ce===expected_ce,"region-order unmasked CE vector");
    if(ce_drift || cycle_drift) begin
      @(negedge clock); #1;
      inject_fault(ce_drift?1:2);
      reject_fault(ce_drift?1:2,ce_drift?"ce-drift":"cycle-drift");
    end
    if(pending_owner || pending_ce || pending_cycle || release_owner || release_ce || release_cycle) begin
      integer kind;
      kind=(pending_owner || release_owner)?0:((pending_ce || release_ce)?1:2);
      begin_pending();
      repeat(8) begin
        @(posedge clock); #2;
        check(capture_response_valid && capture_clock_mask && !capture_request_ready &&
          capture_response_data===64'(expected_ce[0]),"fault setup retains selected response under backpressure");
      end
      if(release_owner || release_ce || release_cycle) begin
        @(negedge clock); #1; freeze_request=0; capture_response_ready=1;
        @(posedge clock); #2; capture_response_ready=0;
        check(!capture_response_valid && capture_clock_mask,"fault setup drained response before release decision");
        @(negedge clock); #1;
      end else begin @(negedge clock); #1; end
      inject_fault(kind);
      reject_fault(kind,rejection_kind);
    end
    allwords();
    readword(254,0,0,0,1); readword(255,4,0,0,1);
    withdrawal();
  endtask
  initial begin
    $dumpfile("native-regions.vcd"); $dumpvars(0,native_regions_common_cut_tb);
    missing_owner=$test$plusargs("missing-owner"); ce_drift=$test$plusargs("ce-drift");
    cycle_drift=$test$plusargs("cycle-drift");
    pending_owner=$test$plusargs("pending-owner"); pending_ce=$test$plusargs("pending-ce");
    pending_cycle=$test$plusargs("pending-cycle"); release_owner=$test$plusargs("release-owner");
    release_ce=$test$plusargs("release-ce"); release_cycle=$test$plusargs("release-cycle");
    rejection_kind=pending_owner?"pending-owner":pending_ce?"pending-ce":pending_cycle?"pending-cycle":
      release_owner?"release-owner":release_ce?"release-ce":"release-cycle";
    repeat(14) @(negedge clock); #1; enable=0;
    repeat(3) @(negedge clock); #1;
    capture_reset=0; reset=0; armed=1;
    active(32); owner_present=!missing_owner;
    // Invalid routes must not manufacture a handshake while execution runs.
    @(negedge clock); #1; capture_bank=254; capture_request_valid=1;
    #1; check(!capture_request_ready && !capture_response_valid,"no request or invalid-route response without a cut");
    @(posedge clock); #2; capture_request_valid=0;
    descriptors();
    for(integer c=0;c<4;c++) begin capture(); active(27+c*7); end
    // Reset cancels a real pending response across the router and both endpoints.
    @(posedge clock); #2; expected_ce={~enable,enable}; freeze_request=1;
    repeat(2) begin @(posedge clock); #2; end
    @(negedge clock); #1; capture_bank=255; capture_slot=0; capture_address=0; capture_request_valid=1;
    @(posedge clock); #2; capture_request_valid=0;
    check(capture_response_valid,"real outstanding response before reset");
    @(negedge clock); #1; capture_reset=1;
    @(posedge clock); #2; check(!capture_response_valid && !capture_request_ready,"shared reset cancels response");
    @(negedge clock); #1; freeze_request=0; capture_reset=0;
    active(21);
    check(words==280 && cuts==4 && withdrawal_stalls==64,"complete four-cut bank/CE/invalid-selector and withdrawal coverage");
    check(requests==responses+1,"only deliberately reset pending response remains unacknowledged");
    check(gate_edges>0,"physical native and root gate outputs observed during active execution");
    $display("NATIVE_COMMON_CUT_DRAIN_PASS requests=%0d responses=%0d withdrawal_stalls=%0d gate_events=%0d",requests,responses,withdrawal_stalls,gate_edges);
    $display("NATIVE_REGIONS_PASS checks=%0d cuts=%0d words=%0d stalls=%0d target_cycle=%0d",checks,cuts,words,stalls,expected_cycle);
    $finish;
  end
  initial begin #1000000; check(0,"watchdog"); end
endmodule
