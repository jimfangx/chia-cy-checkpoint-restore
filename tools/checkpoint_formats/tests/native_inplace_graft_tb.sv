`timescale 1ns/1ps
// Public ports and independent arithmetic/memory oracle; no VCS state access.
module native_inplace_access_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0;
  always #5 clock=!clock;
  reg reset=1, write=0, freeze_request=0, ckpt_reset=1;
  wire ckpt_freeze, read_enable, physical_failed;
  wire [1:0] logical_ce, captured_ce;
  wire [2:0] physical_error;
  wire [63:0] physical_cut_cycle;
  reg owner_present=1;
  reg [1:0] enable=3;
  reg [2:0] address=0;
  reg [129:0] data=0;
  wire [64:0] left_count, right_count, ref_left, ref_right;
  wire [63:0] cycle, ref_cycle;
  wire [129:0] read_data, ref_data;
  reg [7:0] ckpt_bank=0;
  reg [15:0] ckpt_slot=0;
  reg [31:0] ckpt_address=0;
  reg ckpt_req_valid=0, ckpt_resp_ready=0;
  wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error;
  reg [31:0] descriptor_entry=0;
  wire descriptor_valid;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth;
  wire [63:0] ckpt_resp_data;
  NativeInPlaceAccessFixture dut(.*);
  wire reference_clock=clock && !ckpt_freeze;
  NativeReference reference(.clock(reference_clock),.reset(reset),.enable(enable),.address(address),.data(data),.write(write),
    .left_count(ref_left),.right_count(ref_right),.cycle(ref_cycle),.read_data(ref_data));
  reg [64:0] expected_left=0, expected_right=0;
  reg [63:0] expected_cycle=0, expected_raw=0;
  wire [63:0] host_ticks_out, control_ticks_out;
  reg [129:0] memory[0:7];
  reg [129:0] expected_read;
  integer checks=0, cuts=0, words=0, stalls=0;
  bit armed=0, corrupt, missing_owner, drift;
  task check(input bit ok, input string reason);
    checks++;
    if(!ok) begin
      $display("NATIVE_INPLACE_ACCESS_DIVERGENCE reason=%s cycle=%0d checks=%0d",reason,expected_cycle,checks);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  always @(posedge clock) begin
    if(reset) expected_raw=0; else expected_raw++;
    if(!ckpt_freeze) begin
      if(reset) begin
        expected_cycle=0;
        if(enable[0]) expected_left=0;
        if(enable[1]) expected_right=0;
      end else begin
        expected_cycle++;
        if(enable[0]) expected_left++;
        if(enable[1]) expected_right++;
      end
      expected_read=memory[address];
      if(write) memory[address]=data;
    end
    #1;
    if(armed) begin
      check(host_ticks_out===expected_raw && control_ticks_out===expected_raw,
        "both existing ancestor control counters continue on raw clock");
      // Observe only a primitive clock output, never a state backdoor. Freeze
      // muxes could otherwise hide a broken physical root mask from data checks.
      if(ckpt_freeze && !ckpt_reset)
        check(dut.host.stage.network.checkpoint_physical_root_gate_O===0,"physical root clock stopped");
      check(cycle===expected_cycle && left_count===expected_left && right_count===expected_right,
        "independent running/frozen counter arithmetic");
      check(read_data===expected_read,"independent old-read memory pipeline");
      check({cycle,left_count,right_count,read_data}==={ref_cycle,ref_left,ref_right,ref_data},
        "unmodified reference equivalence");
    end
  end
  function automatic [129:0] pattern(input integer t);
    pattern={2'(t%4),64'hfedcba9876543210 ^ (64'(t)*64'h10001),64'h123456789abcdef0 ^ (64'(t)*64'h12345)};
  endfunction
  // The generated selector file contains only independently checked identities,
  // not expected payload values or hierarchy reads.
  `include "native-selectors.svh"
  task readword(input integer selected, input integer at, input reg [63:0] expected, input bit err);
    @(negedge clock); #1;
    ckpt_bank=selected>=65536 || selected==255 ? 255 : 0; ckpt_slot=selected>=65536 ? selected-65536 : selected; ckpt_address=at;
    ckpt_req_valid=1; ckpt_resp_ready=0;
    #1; check(ckpt_req_ready,"ungated bank request ready");
    @(posedge clock); #2;
    ckpt_req_valid=0;
    // Change the route while the request is outstanding, before response-valid.
    ckpt_bank=~ckpt_bank; ckpt_slot=65535; ckpt_address=32'hffffffff;
    for(integer wait_cycles=0;!ckpt_resp_valid && wait_cycles<20;wait_cycles++) begin
      check(!ckpt_req_ready,"pending route blocks another request");
      @(posedge clock); #2;
    end
    check(ckpt_resp_valid && ckpt_resp_error===err && ckpt_resp_data===expected,"latched exact bank word/error");
    for(integer k=0;k<3;k++) begin
      @(negedge clock); #1; ckpt_bank=7; ckpt_slot=65535; ckpt_address=32'hffffffff;
      @(posedge clock); #2; stalls++;
      check(ckpt_resp_valid && !ckpt_req_ready && ckpt_resp_error===err && ckpt_resp_data===expected,
        "held response survives selector changes and backpressure");
    end
    @(negedge clock); #1; ckpt_resp_ready=1;
    @(posedge clock); #2; ckpt_resp_ready=0;
    check(!ckpt_resp_valid,"response drained");
  endtask
  task capture;
    @(posedge clock); #2; freeze_request=1;
    @(negedge clock); #1; check(ckpt_freeze,"mask stops at common low phase");
    @(posedge clock); #2; cuts++;
    if(missing_owner || drift) begin
      if(drift) begin @(negedge clock); #1; enable=~enable; end
      #1; check(physical_failed && !read_enable,"missing owner/CE drift blocks physical read permission");
      if(missing_owner) check(physical_error[0],"missing owner sticky error");
      else begin @(posedge clock); #2; check(physical_error[1],"CE drift sticky error"); end
      @(negedge clock); #1; freeze_request=0;
      repeat(4) begin @(posedge clock); #2; check(physical_failed && ckpt_freeze && !read_enable,"failed cut remains stopped after host withdrawal"); end
      if(missing_owner)
        $display("NATIVE_INPLACE_ACCESS_REJECTED kind=missing-owner cut=%0d checks=%0d",cycle,checks);
      else
        $display("NATIVE_INPLACE_ACCESS_REJECTED kind=ce-drift cut=%0d checks=%0d",cycle,checks);
      $finish;
    end
    check(read_enable && !physical_failed && captured_ce===enable && logical_ce===enable && physical_cut_cycle===cycle,
      "settled physical cut and unmasked CE samples");
    for(integer i=0;i<8;i++) begin
      descriptor_entry=i; #1;
      if(i<7) check(descriptor_valid && descriptor_bank===(i<5 ? 8'd0 : 8'd255) &&
        descriptor_slot===(i<5 ? 16'(i) : 16'(i-5)) &&
        descriptor_width===(i<5 ? 16'd64 : 16'd1) && descriptor_depth===(i<5 ? 32'(depth(i)) : 32'd1),
        "complete descriptor ROM and local CE ordering");
      else check(!descriptor_valid && {descriptor_bank,descriptor_slot,descriptor_width,descriptor_depth}===0,
        "out of range descriptor is empty");
    end
    for(integer i=0;i<2;i++) begin
      readword(65536+i,0,{63'd0,captured_ce[i]},0); words++;
      readword(65536+i,1,0,1);
    end
    for(integer slot=0;slot<5;slot++) begin
      for(integer at=0;at<depth(slot);at++) begin
        reg [63:0] word_value;
        word_value=oracle(slot,at);
        if(corrupt && cuts==1 && slot==0 && at==0) word_value^=1;
        readword(slot,at,word_value,0); words++;
        $display("NATIVE_INPLACE_ACCESS_WORD cut=%0d slot=%0d address=%0d value=%016h",expected_cycle,slot,at,word_value);
      end
      readword(slot,depth(slot),0,1);
    end
    readword(255,0,0,1);
    readword(65535,0,0,1);
    // Synchronous functional reset is dominated by the generated storage freeze.
    // Reset is not a CE input in this fixture. Production reset ownership remains unbound.
    reset=1; repeat(3) begin @(posedge clock); #2; end
    @(negedge clock); #1; reset=0;
    freeze_request=0;
    wait(!ckpt_freeze); #1;
    check(!physical_failed,"healthy cut releases after checked source edge");
  endtask
  initial begin
    $dumpfile("native-inplace-access.vcd"); $dumpvars(0,native_inplace_access_tb);
    corrupt=$test$plusargs("corrupt");
    missing_owner=$test$plusargs("missing-owner"); drift=$test$plusargs("ce-drift");
    owner_present=!missing_owner;
    // Keep functional reset through UNISIM glbl startup and settled gate enables.
    repeat(20) @(posedge clock);
    @(negedge clock); #1; reset=0; ckpt_reset=0;
    readword(65536,0,0,1);
    readword(0,0,0,1);
    for(integer t=0;t<400;t++) begin
      @(negedge clock); #1;
      enable=t<8 ? 3 : (t%4);
      address=t%8; data=pattern(t); write=t<8 || t%3!=0;
      @(posedge clock); #2;
      if(t==9) armed=1;
      if(t==12 || t==63 || t==176 || t==320) capture();
    end
    check(cuts==4 && words==136 && cycle>400,"complete history and resumed functional progress");
    $display("NATIVE_INPLACE_ACCESS_BANK_PASS checks=%0d cuts=%0d words=%0d stalls=%0d cycle=%0d",checks,cuts,words,stalls,cycle);
    $finish;
  end
  initial begin #100000; check(0,"timeout"); end
endmodule
