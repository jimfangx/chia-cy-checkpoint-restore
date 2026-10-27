`timescale 1ns/1ps
// Public ready/valid ports only. The oracle is independent of RTL routing.
module checkpoint_region_router_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0, reset=1;
  always #5 clock=!clock;
  reg request_valid=0, response_ready=0;
  wire request_ready, response_valid, response_error;
  reg [7:0] bank=0;
  reg [15:0] slot=0;
  reg [31:0] address=0;
  wire [63:0] response_data;
  wire [1:0] region_request_valid, region_response_ready;
  reg [1:0] region_request_ready=0;
  wire [1:0] region_response_valid, region_response_error;
  wire [127:0] region_response_data;
  wire [7:0] region_bank;
  wire [15:0] region_slot;
  wire [31:0] region_address;
  CheckpointRegionStateRouter #(
    `include "parameters.svh"
  ) dut(.*);
  reg [1:0] saved_pending=0;
  reg [63:0] saved_data[0:1];
  reg saved_error[0:1];
  integer delay[0:1];
  integer checks=0, requests=0, responses=0, invalids=0, stalls=0, resets=0;
  task check(input bit ok, input string reason);
    checks++;
    if(!ok) begin
      $display("REGION_ROUTER_DIVERGENCE reason=%s requests=%0d responses=%0d bank=%0d slot=%0d",
        reason,requests,responses,bank,slot);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  for(genvar k=0;k<2;k++) begin: endpoint
    // Unsolicited idle responses intentionally remain asserted. They may never
    // steal an outstanding response or be acknowledged without a request.
    assign region_response_valid[k] = saved_pending[k] ? delay[k]==0 : 1'b1;
    assign region_response_data[k*64 +: 64] = saved_pending[k] ? saved_data[k] : 64'hdeaddeadbeefbeef;
    assign region_response_error[k] = saved_pending[k] ? saved_error[k] : 1'b1;
    always @(posedge clock) begin
      if(reset) begin saved_pending[k]<=0; delay[k]<=0; end
      else begin
        if(delay[k]>0) delay[k]<=delay[k]-1;
        if(region_request_valid[k] && region_request_ready[k]) begin
          check(!saved_pending[k],"one outstanding endpoint read");
          saved_pending[k]<=1; delay[k]<=3;
          saved_data[k]<={8'(8'hc0+k),region_bank,region_slot,region_address};
          saved_error[k]<=region_address>=16 || (region_bank==255 && region_slot>=2);
        end
        if(region_response_ready[k] && region_response_valid[k]) begin
          check(saved_pending[k] && delay[k]==0,"no unsolicited/wrong-region acknowledgement");
          saved_pending[k]<=0;
        end
      end
    end
  end
  task tick; @(posedge clock); #2; endtask
  task begin_request(input integer b, input integer s, input integer a,
      input integer target, input integer local_bank, input integer local_slot);
    @(negedge clock); #1;
    bank=b; slot=s; address=a; request_valid=1;
    region_request_ready=target<0 ? 0 : (2'b11 ^ (2'b01<<target));
    repeat(target<0 ? 1 : 4) begin
      #1;
      check(!response_valid && region_response_ready==0,"idle noise cannot answer request");
      if(target<0) check(request_ready && region_request_valid==0,"invalid selector terminates locally");
      else check(!request_ready && region_request_valid==(2'b01<<target) &&
        region_bank==local_bank && region_slot==local_slot && region_address==a,
        "exclusive local selectors under request backpressure");
      // Invalid requests are ready immediately, so do not advance until accepted.
      if(target>=0) begin tick; stalls++; @(negedge clock); #1; end
    end
    region_request_ready=3;
    #1; check(request_ready,"request accepted only by chosen ready region");
    tick; request_valid=0; requests++;
    if(target<0) invalids++;
  endtask
  task complete(input integer target, input reg [63:0] expected, input bit err);
    // Replace upstream selectors and poison the unselected response throughout.
    @(negedge clock); #1; bank=254; slot=65535; address=32'hffffffff; request_valid=1;
    if(target>=0) begin
      repeat(2) begin
        tick; check(!response_valid && region_response_ready==0,"selected delayed response only");
        @(negedge clock); #1;
      end
      tick;
    end
    repeat(8) begin
      #1;
      check(!request_ready && region_request_valid==0 && region_response_ready==0,
        "pending response pins owner and blocks replacement");
      check(response_valid && response_data===expected && response_error===err,
        "routed payload/error before acknowledgement");
      tick; stalls++; @(negedge clock); #1;
    end
    response_ready=1;
    #1; check(region_response_ready==(target<0 ? 0 : (2'b01<<target)),"exclusive response acknowledgement");
    tick; responses++; request_valid=0; response_ready=0;
    check(!response_valid && response_data==0 && !response_error && region_response_ready==0,"idle outputs clear");
  endtask
  task transaction(input integer b, input integer s, input integer a,
      input integer target, input integer local_bank, input integer local_slot);
    reg [63:0] expected;
    expected=target<0 ? 0 : {8'(8'hc0+target),8'(local_bank),16'(local_slot),32'(a)};
    begin_request(b,s,a,target,local_bank,local_slot);
    complete(target,expected,target<0 || $unsigned(a)>=16 || (local_bank==255 && local_slot>=2));
  endtask
  task cancel(input bit held);
    begin_request(1,1,4,1,0,1);
    if(held) repeat(5) tick;
    @(negedge clock); #1; reset=1; response_ready=1; request_valid=1;
    #1; check(!request_ready && !response_valid && region_request_valid==0 && region_response_ready==0,
      "reset suppresses every handshake");
    tick; resets++;
    @(negedge clock); #1; reset=0; response_ready=0; request_valid=0;
    #1; check(!response_valid && region_response_ready==0,"reset cancels owner and endpoints together");
    transaction(0,2,3,0,0,2);
  endtask
  initial begin
    $dumpfile("region-router.vcd"); $dumpvars(0,checkpoint_region_router_tb);
    #1; check(!request_ready && !response_valid && region_request_valid==0 && region_response_ready==0,"initial reset");
    tick; @(negedge clock); #1; reset=0;
    for(integer i=0;i<32;i++) begin
      transaction(0,i%8,i%17,0,0,i%8);
      transaction(1,i%8,i%17,1,0,i%8);
      transaction(2,i%8,i%17,1,1,i%8);
      transaction(255,0,0,0,255,0);
      transaction(255,1,0,1,255,0);
      transaction(255,2,0,1,255,1);
    end
    transaction(3,0,0,-1,0,0); transaction(254,0,0,-1,0,0);
    transaction(255,3,0,-1,0,0); transaction(255,65535,0,-1,0,0);
    // Bound checks belong to the selected endpoint and propagate unchanged.
    transaction(0,65535,32'hffffffff,0,0,65535);
    cancel(0); cancel(1);
    check(requests==responses+resets,"each accepted request is returned or explicitly reset");
    $display("REGION_ROUTER_PASS checks=%0d requests=%0d responses=%0d invalids=%0d stalls=%0d resets=%0d",
      checks,requests,responses,invalids,stalls,resets);
    $finish;
  end
  initial begin #1000000; check(0,"watchdog"); end
endmodule
