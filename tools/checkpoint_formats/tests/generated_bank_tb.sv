`timescale 1ns/1ps
module generated_bank_tb;
  reg clock=0, reset=1;
  reg [8:0] data=0;
  reg [2:0] addr=0;
  reg wen=0;
  wire [8:0] result;
  reg ckpt_freeze=0, ckpt_reset=1, ckpt_req_valid=0, ckpt_resp_ready=0;
  reg [7:0] ckpt_bank=0;
  reg [15:0] ckpt_slot=0;
  reg [31:0] ckpt_address=0;
  wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error, ckpt_match;
  wire [63:0] ckpt_resp_data, ckpt_data;
  Harness dut(.*);

  integer checks=0, reads=0, stalls=0, edges=0;
  reg ref_harness=0;
  reg [8:0] ref_counter=0, ref_bank[0:2], ref_left=0, ref_right=0, ref_mem[0:7];
  reg [1:0] ref_fsm=0;
  // This oracle implements the original fixture's functional specification.
  // It observes only driven inputs and the public freeze; no hierarchy access.
  always @(posedge clock) begin
    if (!ckpt_freeze) begin
      edges=edges+1;
      ref_harness = reset ? 0 : !ref_harness;
      ref_counter = reset ? 0 : ref_counter + 1;
      ref_fsm = reset ? 0 : ((ref_fsm == 2) ? 0 : ref_fsm + 1);
      ref_bank[0]=data; ref_bank[1]=data+1; ref_bank[2]=data+2;
      ref_left=reset ? 0 : data; ref_right=reset ? 0 : data+1;
      if (wen) ref_mem[addr]=data;
    end
  end
  task tick;
    begin #5; clock=1; #1; clock=0; #4; end
  endtask
  task check(input bit condition, input string message);
    begin
      checks=checks+1;
      if (!condition) begin $display("GENERATED_BANK_FAIL %s checks=%0d",message,checks); $fatal(1); end
    end
  endtask
  function automatic [63:0] oracle(input integer kind, input integer address);
    case(kind)
      0: oracle=ref_harness;
      1: oracle=ref_counter;
      2: oracle=ref_fsm;
      3: oracle=ref_bank[0];
      4: oracle=ref_bank[1];
      5: oracle=ref_bank[2];
      6: oracle=ref_left;
      7: oracle=ref_right;
      8: oracle=ref_mem[address];
      default: begin $fatal(1,"unknown oracle kind"); oracle=0; end
    endcase
  endfunction
  task read_word(input [7:0] bank, input [15:0] slot, input [31:0] address,
                 input [63:0] expected, input bit error, input integer delay_cycles,
                 input bit release_freeze);
    integer j;
    begin
      ckpt_bank=bank; ckpt_slot=slot; ckpt_address=address;
      ckpt_req_valid=1; ckpt_resp_ready=0; #1;
      check(ckpt_req_ready===1,"ready before request");
      tick(); ckpt_req_valid=0; reads=reads+1;
      for(j=0;j<delay_cycles+1;j=j+1) begin
        if (release_freeze) begin ckpt_freeze=0; reset=0; wen=1; data=data+7; end
        ckpt_bank=8'hff; ckpt_slot=16'hffff; ckpt_address=32'hffffffff;
        #1;
        check(ckpt_resp_valid===1,"registered response valid");
        check(ckpt_req_ready===0,"one outstanding read");
        check(ckpt_resp_error===error,"response error");
        check(ckpt_resp_data===expected,$sformatf("latched response data got=%h expected=%h",ckpt_resp_data,expected));
        tick(); stalls=stalls+1;
      end
      ckpt_resp_ready=1; tick(); ckpt_resp_ready=0; #1;
      check(ckpt_resp_valid===0,"response retired exactly once");
      check(ckpt_req_ready===1,"ready after response retirement");
    end
  endtask
  integer i,a;
  `include "generated_bank_bindings.svh"
  initial begin
    #1; tick(); tick(); ckpt_reset=0;
    for(i=0;i<8;i=i+1) begin data=100+i; addr=i; wen=1; tick(); end
    reset=0;
    for(i=0;i<7;i=i+1) begin data=200+i; addr=i; wen=1; tick(); end
    // Accepting-edge freeze must defeat both a functional reset and a write.
    ckpt_freeze=1; reset=1; data=511; addr=0; wen=1;
    for(i=0;i<ENTRY_COUNT;i=i+1)
      for(a=0;a<depths[i];a=a+1)
        read_word(banks[i],slots[i],a,oracle(kinds[i],a),0,(i+a)%4,0);
    // Invalid selectors fail canonically without reading some other state.
    read_word(8'hff,0,0,0,1,3,0);
    read_word(banks[0],16'hffff,0,0,1,2,0);
    read_word(banks[0],slots[0],depths[0],0,1,1,0);
    // Abort/release while a delayed response is held cannot change that beat.
    read_word(banks[0],slots[0],0,oracle(kinds[0],0),0,5,1);
    // Reads while running return an explicit error, not an incoherent value.
    read_word(banks[0],slots[0],0,0,1,1,0);
    ckpt_freeze=1; reset=1; data=509; wen=1; addr=3;
    for(i=0;i<ENTRY_COUNT;i=i+1)
      for(a=0;a<depths[i];a=a+1)
        read_word(banks[i],slots[i],a,oracle(kinds[i],a),0,(i+a)%3,0);
    ckpt_freeze=0; reset=0; wen=0; tick();
    ckpt_freeze=1;
    for(i=0;i<ENTRY_COUNT;i=i+1)
      for(a=0;a<depths[i];a=a+1)
        read_word(banks[i],slots[i],a,oracle(kinds[i],a),0,0,0);
    $display("GENERATED_BANK_PASS checks=%0d reads=%0d stalls=%0d functional_edges=%0d",checks,reads,stalls,edges);
    $finish;
  end
  initial begin #1000000; $fatal(1,"watchdog"); end
endmodule
