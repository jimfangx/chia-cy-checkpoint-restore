`timescale 1ns/1ps
module production_bank_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, otherClock=0, reset=1, ckpt_clock=0;
  reg ckpt_reset=1, ckpt_freeze=0, ckpt_req_valid=0, ckpt_resp_ready=0;
  reg [7:0] ckpt_bank=0;
  reg [15:0] ckpt_slot=0;
  reg [31:0] ckpt_address=0;
  wire [7:0] count, injected;
  wire ckpt_match, ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error;
  wire [63:0] ckpt_data, ckpt_resp_data;
  HostPipeline dut(.*);
  integer checks=0, edges=0, host_ticks=0, reads=0, cuts=0, i, stall;
  reg [7:0] expected_count=0, expected_injected=19;
  reg corrupt;
  task check(input bit ok, input string why);
    begin
      checks=checks+1;
      if (!ok) begin
        $display("PRODUCTION_BANK_MISMATCH target_cycle=%0d reads=%0d freeze=%0d reason=%s",
          edges, reads, ckpt_freeze, why);
        checkpoint_network_fail();
      end
    end
  endtask
  task functional_tick;
    begin
      #2; clock=1; host_ticks=host_ticks+1;
      if (!ckpt_freeze) begin
        edges=edges+1;
        if (reset) begin expected_count=0; expected_injected=19; end
        else begin expected_count=expected_count+1; expected_injected=expected_injected+3; end
      end
      #1;
      check(count===expected_count && injected===expected_injected, "functional output");
      clock=0;
      repeat (3) begin
        #1; otherClock=1; #1;
        check(count===expected_count && injected===expected_injected, "unrelated clock");
        otherClock=0;
      end
    end
  endtask
  task access_tick;
    begin #2; ckpt_clock=1; #1; ckpt_clock=0; #1; end
  endtask
  task read_word(input [7:0] bank, input [15:0] slot, input [31:0] addr,
                 input [63:0] expected, input bit error_expected);
    reg [63:0] observed;
    integer cut_cycle;
    begin
      cut_cycle=edges;
      check(ckpt_req_ready===1'b1 && ckpt_resp_valid===1'b0, "ready before request");
      ckpt_bank=bank; ckpt_slot=slot; ckpt_address=addr; ckpt_req_valid=1;
      access_tick(); ckpt_req_valid=0;
      check(ckpt_resp_valid===1'b1 && ckpt_req_ready===1'b0, "latched response");
      observed=ckpt_resp_data ^ ((corrupt && !error_expected) ? 64'd1 : 64'd0);
      check(observed===expected && ckpt_resp_error===error_expected, "complete bank word");
      for (stall=0;stall<4;stall=stall+1) begin
        // Selectors change after acceptance. The response must stay latched.
        ckpt_bank=8'hff; ckpt_slot=16'hffff; ckpt_address=32'hffffffff;
        access_tick();
        check(ckpt_resp_valid===1'b1 && ckpt_resp_data===expected &&
              ckpt_resp_error===error_expected, "stalled response");
        if (ckpt_freeze) begin
          reset=1; functional_tick(); reset=0;
          check(edges==cut_cycle, "no functional edge during freeze");
        end
      end
      ckpt_resp_ready=1; access_tick(); ckpt_resp_ready=0;
      check(ckpt_resp_valid===1'b0 && ckpt_req_ready===1'b1, "response acknowledged");
      reads=reads+1;
    end
  endtask
  task capture;
    begin
      ckpt_freeze=1; #1;
      read_word(0,`COUNT_SLOT,0,{56'd0,expected_count},0);
      read_word(0,`HOST_SLOT,0,{56'd0,expected_injected},0);
      read_word(1,0,0,0,1);
      read_word(0,16'hffff,0,0,1);
      read_word(0,`HOST_SLOT,32'hffffffff,0,1);
      $display("PRODUCTION_BANK_CUT target_cycle=%0d count=%0d injected=%0d complete_words=2",
        edges,expected_count,expected_injected);
      cuts=cuts+1; ckpt_freeze=0;
    end
  endtask
  initial begin
    corrupt=$test$plusargs("corrupt");
    $dumpfile("production-bank.vcd"); $dumpvars(0,production_bank_tb);
    access_tick(); ckpt_reset=0; access_tick();
    functional_tick(); reset=0;
    for(i=0;i<1024;i=i+1) begin
      reset=(i==511 || i==512); functional_tick(); reset=0;
      if (edges==2 || edges==39 || edges==132 || edges==900) capture();
    end
    // Unfrozen access is an error, never a partial read.
    read_word(0,`HOST_SLOT,0,0,1);
    check(cuts==4 && reads==21 && edges==1025, "complete execution");
    $display("PRODUCTION_BANK_PASS checks=%0d edges=%0d host_ticks=%0d reads=%0d cuts=%0d",
      checks,edges,host_ticks,reads,cuts);
    $finish;
  end
endmodule
