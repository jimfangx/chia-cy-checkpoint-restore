`timescale 1ns/1ps
module physical_state_router_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, reset=1;
  always #5 clock=!clock;
  reg [31:0] descriptor_entry=0;
  wire descriptor_valid;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth, functional_descriptor_entry, ce_descriptor_entry;
  reg functional_descriptor_valid=1, ce_descriptor_valid=1;
  reg [7:0] functional_descriptor_bank=2, ce_descriptor_bank=255;
  reg [15:0] functional_descriptor_slot=7, functional_descriptor_width=32;
  reg [15:0] ce_descriptor_slot=0, ce_descriptor_width=1;
  reg [31:0] functional_descriptor_depth=8, ce_descriptor_depth=1;
  reg request_valid=0, response_ready=0;
  wire request_ready, response_valid, response_error;
  reg [7:0] bank=2;
  reg [15:0] slot=7;
  reg [31:0] address=3;
  wire [63:0] response_data;
  wire functional_request_valid, ce_request_valid;
  reg functional_request_ready=0, ce_request_ready=0;
  wire [7:0] endpoint_bank;
  wire [15:0] endpoint_slot;
  wire [31:0] endpoint_address;
  reg functional_response_valid=0, ce_response_valid=0;
  wire functional_response_ready, ce_response_ready;
  reg [63:0] functional_response_data=64'h1234, ce_response_data=1;
  reg functional_response_error=0, ce_response_error=0;
  CheckpointPhysicalStateRouter #(.ENTRIES(2),.GATES(3)) dut(.*);
  integer checks=0;
  bit corrupt;
  task check(input bit ok, input string reason);
    checks++;
    if(!ok) begin
      $display("PHYSICAL_ROUTER_DIVERGENCE reason=%s acknowledged_edges=0",reason);
      checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task tick; @(posedge clock); #2; endtask
  task invalid_descriptor;
    #1; check(!descriptor_valid && descriptor_bank==0 && descriptor_slot==0 &&
      descriptor_width==0 && descriptor_depth==0,"invalid descriptor cannot alias state");
  endtask
  task transaction(input bit physical, input bit err);
    @(negedge clock); #1;
    bank=physical ? 255 : 2; slot=physical ? 1 : 7; address=physical ? 0 : 3;
    request_valid=1; functional_request_ready=0; ce_request_ready=0;
    repeat(4) begin
      tick;
      check(!request_ready && !response_valid && !functional_response_ready && !ce_response_ready,
        "request backpressure creates no response owner");
      check(functional_request_valid==!physical && ce_request_valid==physical &&
        endpoint_bank==bank && endpoint_slot==slot && endpoint_address==address,"exclusive request selectors");
    end
    @(negedge clock); #1; functional_request_ready=1; ce_request_ready=1; #1;
    check(request_ready,"selected endpoint ready"); tick;
    request_valid=0;
    // Both endpoints may present a response. Only the accepted destination is
    // entitled to drive upstream, even when upstream selectors change.
    for(integer i=0;i<12;i++) begin
      @(negedge clock); #1;
      bank=physical ? 0 : 255; slot=65535; address=32'hffffffff;
      functional_response_valid=1; ce_response_valid=1;
      functional_response_error=err; ce_response_error=err;
      response_ready=0; request_valid=1;
      tick;
      check(!request_ready && !functional_request_valid && !ce_request_valid,"outstanding read blocks replacement");
      check(response_valid && response_data==(physical ? (corrupt ? 0 : 1) : 64'h1234) && response_error==err,
        "accepted destination pinned under selector changes");
      check(!functional_response_ready && !ce_response_ready,"response backpressure");
    end
    @(negedge clock); #1; response_ready=1; #1;
    check(functional_response_ready==!physical && ce_response_ready==physical,"only selected response drains");
    tick; request_valid=0; response_ready=0;
    check(!response_valid && response_data==0 && !response_error &&
      !functional_response_ready && !ce_response_ready,"unsolicited endpoint responses ignored");
    functional_response_valid=0; ce_response_valid=0;
  endtask
  initial begin
    $dumpfile("physical-router.vcd"); $dumpvars(0,physical_state_router_tb);
    corrupt=$test$plusargs("corrupt");
    #1; check(!request_ready && !response_valid && !functional_request_valid && !ce_request_valid,"reset suppresses handshakes");
    tick; @(negedge clock); #1; reset=0;
    for(integer i=0;i<2;i++) begin
      descriptor_entry=i; #1;
      check(descriptor_valid && descriptor_bank==2 && descriptor_slot==7 && descriptor_width==32 &&
        descriptor_depth==8 && functional_descriptor_entry==i && ce_descriptor_entry==32'hffffffff,
        "functional descriptor ordinal preserved");
    end
    functional_descriptor_bank=255; invalid_descriptor(); functional_descriptor_bank=2;
    functional_descriptor_width=0; invalid_descriptor(); functional_descriptor_width=65; invalid_descriptor();
    functional_descriptor_width=32; functional_descriptor_depth=0; invalid_descriptor(); functional_descriptor_depth=8;
    functional_descriptor_valid=0; invalid_descriptor(); functional_descriptor_valid=1;
    for(integer i=0;i<3;i++) begin
      descriptor_entry=2+i; ce_descriptor_slot=i; #1;
      check(descriptor_valid && descriptor_bank==255 && descriptor_slot==i && descriptor_width==1 &&
        descriptor_depth==1 && ce_descriptor_entry==i && functional_descriptor_entry==32'hffffffff,
        "physical descriptor appended in slot order");
      ce_descriptor_slot=3; invalid_descriptor(); ce_descriptor_slot=i;
      ce_descriptor_bank=2; invalid_descriptor(); ce_descriptor_bank=255;
      ce_descriptor_width=2; invalid_descriptor(); ce_descriptor_width=1;
      ce_descriptor_depth=2; invalid_descriptor(); ce_descriptor_depth=1;
      ce_descriptor_valid=0; invalid_descriptor(); ce_descriptor_valid=1;
    end
    descriptor_entry=5; invalid_descriptor(); descriptor_entry=32'hffffffff; invalid_descriptor();
    transaction(0,0); transaction(1,0); transaction(0,1); transaction(1,1);
    // Reset between edges cancels an accepted transaction immediately; the
    // common endpoint reset then removes its response before a fresh request.
    @(negedge clock); #1; bank=255; request_valid=1; tick;
    @(negedge clock); #1; reset=1; ce_response_valid=1; response_ready=1; #1;
    check(!request_ready && !response_valid && !ce_response_ready && !functional_response_ready,"reset cancels held route immediately");
    tick; request_valid=0; ce_response_valid=0; response_ready=0;
    @(negedge clock); #1; reset=0;
    transaction(0,0); transaction(1,0);
    $display("PHYSICAL_ROUTER_PASS checks=%0d transactions=6",checks); $finish;
  end
  initial begin #20000; check(0,"timeout"); end
endmodule
