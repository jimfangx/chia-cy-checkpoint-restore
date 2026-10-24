`timescale 1ns/1ps
// Public ports and independent arithmetic/memory oracle; no VCS state access.
module native_functional_bank_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0;
  always #5 clock=!clock;
  reg reset=1, write=0, ckpt_freeze=0, ckpt_reset=1;
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
  wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error, ckpt_match;
  wire [63:0] ckpt_resp_data, ckpt_data;
  NativeStorage dut(.clock(clock),.reset(reset),.enable(enable),.address(address),.data(data),.write(write),
    .left_count(left_count),.right_count(right_count),.cycle(cycle),.read_data(read_data),
    .ckpt_clock(clock),.ckpt_freeze(ckpt_freeze),.ckpt_reset(ckpt_reset),
    .ckpt_bank(ckpt_bank),.ckpt_slot(ckpt_slot),.ckpt_address(ckpt_address),.ckpt_match(ckpt_match),.ckpt_data(ckpt_data),
    .ckpt_req_valid(ckpt_req_valid),.ckpt_req_ready(ckpt_req_ready),.ckpt_resp_valid(ckpt_resp_valid),
    .ckpt_resp_ready(ckpt_resp_ready),.ckpt_resp_data(ckpt_resp_data),.ckpt_resp_error(ckpt_resp_error));
  wire reference_clock=clock && !ckpt_freeze;
  NativeReference reference(.clock(reference_clock),.reset(reset),.enable(enable),.address(address),.data(data),.write(write),
    .left_count(ref_left),.right_count(ref_right),.cycle(ref_cycle),.read_data(ref_data));
  reg [64:0] expected_left=0, expected_right=0;
  reg [63:0] expected_cycle=0;
  reg [129:0] memory[0:7];
  reg [129:0] expected_read;
  integer checks=0, cuts=0, words=0, stalls=0;
  bit armed=0, corrupt;
  task check(input bit ok, input string reason);
    checks++;
    if(!ok) begin
      $display("NATIVE_FUNCTIONAL_DIVERGENCE reason=%s cycle=%0d checks=%0d",reason,expected_cycle,checks);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  always @(posedge clock) begin
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
    ckpt_bank=selected==255 ? 255 : 0; ckpt_slot=selected; ckpt_address=at;
    ckpt_req_valid=1; ckpt_resp_ready=0;
    #1; check(ckpt_req_ready,"ungated bank request ready");
    @(posedge clock); #2;
    ckpt_req_valid=0;
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
    @(negedge clock); #1; ckpt_freeze=1;
    @(posedge clock); #2; cuts++;
    for(integer slot=0;slot<5;slot++) begin
      for(integer at=0;at<depth(slot);at++) begin
        reg [63:0] word_value;
        word_value=oracle(slot,at);
        if(corrupt && cuts==1 && slot==0 && at==0) word_value^=1;
        readword(slot,at,word_value,0); words++;
        $display("NATIVE_BANK_WORD cut=%0d slot=%0d address=%0d value=%016h",expected_cycle,slot,at,word_value);
      end
      readword(slot,depth(slot),0,1);
    end
    readword(255,0,0,1);
    readword(65535,0,0,1);
    // Endpoint reset must clear a held response without disturbing functional state.
    @(negedge clock); #1; ckpt_slot=0; ckpt_bank=0; ckpt_address=0; ckpt_req_valid=1;
    @(posedge clock); #2; ckpt_req_valid=0; check(ckpt_resp_valid,"pending before endpoint reset");
    @(negedge clock); #1; ckpt_reset=1;
    @(posedge clock); #2; check(!ckpt_resp_valid && !ckpt_req_ready,"endpoint reset cancels held response");
    @(negedge clock); #1; ckpt_reset=0;
    // Synchronous functional reset is dominated by the generated storage freeze.
    // Its external owner is still unbound: this is no production reset admission.
    reset=1; repeat(3) begin @(posedge clock); #2; end
    @(negedge clock); #1; reset=0;
    ckpt_freeze=0;
  endtask
  initial begin
    $dumpfile("native-functional.vcd"); $dumpvars(0,native_functional_bank_tb);
    corrupt=$test$plusargs("corrupt");
    // Keep functional reset through UNISIM glbl startup and settled gate enables.
    repeat(20) @(posedge clock);
    @(negedge clock); #1; reset=0; ckpt_reset=0;
    for(integer t=0;t<400;t++) begin
      @(negedge clock); #1;
      enable=t<8 ? 3 : (t%4);
      address=t%8; data=pattern(t); write=t<8 || t%3!=0;
      @(posedge clock); #2;
      if(t==9) armed=1;
      if(t==12 || t==63 || t==176 || t==320) capture();
    end
    check(cuts==4 && words==128 && cycle>400,"complete history and resumed functional progress");
    $display("NATIVE_FUNCTIONAL_BANK_PASS checks=%0d cuts=%0d words=%0d stalls=%0d cycle=%0d",checks,cuts,words,stalls,cycle);
    $finish;
  end
  initial begin #100000; check(0,"timeout"); end
endmodule
