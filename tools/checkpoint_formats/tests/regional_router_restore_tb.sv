`timescale 1ns/1ps
// Generated original host and its actual readout adapter. Only ROUTER state is
// migrated. Matching endpoints are deliberately prepared through public reads;
// this fixture cannot establish endpoint, global-cut or CPU migration.
module regional_router_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer N=`REGIONS, BITS=3+2*N;
  reg clock=0; always #5 clock=!clock;
  reg reset=1, capture_reset=1, freeze_request=0, owner_present=1, write=0;
  reg [1:0] enable=3;
  reg [2:0] address=0;
  reg [129:0] data=0;
  wire [64:0] left_count, right_count, other_left_count, other_right_count;
  wire [63:0] cycle, other_cycle, host_ticks_out, control_ticks_out;
  wire [129:0] read_data, other_read_data;
  wire capture_clock_mask, capture_read_enable, failed;
  wire [2*N-1:0] capture_logical_ce, capture_captured_ce;
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
  reg capture_router_restore_hold=0, capture_router_restore_load=0;
  reg [BITS-1:0] capture_router_restore_state=0;
  wire [BITS-1:0] capture_router_state;
  wire capture_router_restore_ready, capture_router_restore_error;
  NativeRegionsFixture dut(.*);
  string mode, image;
  integer fd, snapshots=0, checks=0, requests=0, responses=0, corrupt_bit=-1;
  reg [BITS-1:0] donor, prior;
  reg [63:0] label;
  bit destination;
  task check(input bit ok, input string why);
    checks++;
    if (!ok) begin
      $display("REGIONAL_ROUTER_FAILURE reason=%s snapshot=%0d target_cycle=%0d requests=%0d responses=%0d",why,snapshots,cycle,requests,responses);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  always @(posedge clock) if(!capture_reset) begin
    if(capture_request_valid && capture_request_ready) requests++;
    if(capture_response_valid && capture_response_ready) responses++;
  end
  task tick; @(posedge clock); #2; endtask
  task low; @(negedge clock); #1; endtask
  task blocked;
    check(!capture_request_ready && !capture_response_valid,"held upstream handshakes");
  endtask
  task load(input reg [BITS-1:0] value);
    capture_router_restore_state=value; capture_router_restore_load=1;
    #1; check(capture_router_restore_ready && !capture_router_restore_error,"complete valid load admission"); blocked();
    tick(); capture_router_restore_load=0; #1;
    check(capture_router_state===value,"all original router bits loaded atomically"); blocked();
  endtask
  task record;
    low();
    if(!destination) $fdisplay(fd,"%h %h",capture_router_state,cycle);
    else begin
      check($fscanf(fd,"%h %h",donor,label)==2,"complete independent donor record");
      check(label===cycle,"donor target-cycle identity");
      capture_router_restore_hold=1; #1;
      capture_router_restore_state=donor ^ (corrupt_bit>=0 && snapshots==0 ? (BITS'(1)<<corrupt_bit) : BITS'(0));
      capture_router_restore_load=1; #1;
      check(capture_router_restore_ready && !capture_router_restore_error,"donor load admitted"); blocked();
      tick(); capture_router_restore_load=0; #1;
      if(capture_router_state!==donor) begin
        $display("REGIONAL_ROUTER_FIRST_DIVERGENCE signal=capture_router_state snapshot=%0d target_cycle=%0d expected=%0d observed=%0d acknowledged_edges=%0d",snapshots,cycle,donor,capture_router_state,requests+responses);
        checkpoint_widget_failed(); $finish;
      end
      // Input selectors and unsolicited upstream traffic cannot alter held state.
      capture_request_valid=1; capture_response_ready=1;
      repeat(3) begin tick(); blocked(); check(capture_router_state===donor,"complete held donor readback"); end
      low(); capture_request_valid=0; capture_response_ready=0; capture_router_restore_hold=0; #1;
    end
    snapshots++;
  endtask
  task request(input integer bank, input integer slot);
    low(); capture_bank=bank; capture_slot=slot; capture_address=0; capture_request_valid=1;
    #1; check(capture_request_ready,"actual generated request accepted");
    tick(); capture_request_valid=0;
    for(integer k=0;!capture_response_valid && k<10;k++) tick();
    check(capture_response_valid,"actual generated response outstanding");
  endtask
  task drain(input reg [63:0] expected, input bit expected_error);
    check(capture_response_valid && capture_response_data===expected && capture_response_error===expected_error,"actual selected endpoint response");
    low(); capture_response_ready=1; tick(); capture_response_ready=0;
    check(!capture_response_valid,"actual response acknowledged once");
  endtask
  initial begin
    $dumpfile("regional-router-restore.vcd"); $dumpvars(0,regional_router_restore_tb);
    check($value$plusargs("mode=%s",mode) && $value$plusargs("image=%s",image),"explicit invocation");
    destination=mode=="destination";
    if($value$plusargs("corrupt_bit=%d",corrupt_bit)) check(destination,"destination corruption only");
    fd=$fopen(image,destination?"r":"w");check(fd!=0,"open independent router donor");
    // Cover vendor global reset and reset both complementary gated executions.
    repeat(14) tick(); low(); enable=0; repeat(3) tick();
    low(); enable=3; reset=0; capture_reset=0;
    for(integer k=0;k<37;k++) begin
      tick();
      if(k<36) begin low();enable=k%4; end
    end
    low();enable=3;
    // Settle CE during a running target edge, then take cut 38.
    tick();freeze_request=1;
    repeat(3) tick(); check(capture_read_enable && !failed,"explicit fixture cut");
    record();
    for(integer r=0;r<N;r++) begin
      // cycles is a real functional descriptor, emitted from its manifest.
      request(r,r==0?`CYCLE_SLOT0:`CYCLE_SLOT1); record(); drain(cycle,0); record();
      request(255,2*r); record(); drain(r==0?1:0,0); record();
    end
    request(254,0); record(); drain(0,1); record();
    if(destination) begin
      // Exhaust every complete ABI encoding, including mutually inconsistent
      // endpoint pending bits. These are router-only readbacks under hold; the
      // endpoint owners are explicitly outside this restore contract.
      low(); capture_router_restore_hold=1;
      for(integer value=0;value<(1<<BITS);value++) begin
        if(((value>>2)&1)<N) begin load(BITS'(value)); low(); end
      end
      prior=capture_router_state;
      // Invalid complete owner must preserve EVERY physical router too.
      if(N==1) begin
        capture_router_restore_state='1;capture_router_restore_load=1;#1;
        check(!capture_router_restore_ready && capture_router_restore_error,"invalid complete owner rejected");
        tick();capture_router_restore_load=0;#1;
        check(capture_router_state===prior,"invalid owner has no partial physical load");
      end
      // Withdrawing the physical cut, and an unheld load, both reject globally.
      low();freeze_request=0; repeat(3) tick();
      capture_router_restore_state=0;capture_router_restore_load=1;#1;
      check(!capture_router_restore_ready && capture_router_restore_error,"lost physical cut rejected");
      tick();check(capture_router_state===prior,"unsafe cut preserves complete vector");
      low();capture_router_restore_hold=0;freeze_request=1;repeat(3) tick();
      #1;check(capture_router_restore_error,"unheld load rejected");blocked();
      tick();check(capture_router_state===prior,"unheld load preserves all routers");
      low();capture_router_restore_hold=1;load(0);low();
      // Shared reset dominates loading and cancels every original router owner.
      capture_router_restore_state='1;capture_router_restore_load=1;capture_reset=1;
      tick();check(capture_router_state===0,"common reset dominates complete loading");
      low();capture_router_restore_load=0;capture_router_restore_hold=0;capture_reset=0; #1;
    end
    $fclose(fd);
    check(snapshots==4*N+3,"complete donor selection coverage");
    check(requests==2*N+1 && responses==requests,"healthy actual readout completion");
    $display("REGIONAL_ROUTER_RESTORE_PASS regions=%0d snapshots=%0d requests=%0d responses=%0d checks=%0d",N,snapshots,requests,responses,checks);
    $finish;
  end
  initial begin #1000000;check(0,"watchdog");end
endmodule
