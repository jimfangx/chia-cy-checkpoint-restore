`timescale 1ns/1ps
module live_shell_snapshot_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=~clock;
  reg reset=1, freeze=0, bank_reset=1, request=0, release_snapshot=0, snapshot_reset=1;
  reg owners_present=1, owners_frozen=1, req_valid=0, resp_ready=0;
  reg [7:0] bank=0; reg [15:0] slot=0; reg [31:0] address=0, word_address=0;
  reg [63:0] target_cycle=0;
  wire [63:0] value, response_data, word_data, cut_cycle;
  wire [236:0] live;
  wire [307:0] control_state;
  wire ready,valid,borrow_enable,failed,word_error,req_ready,resp_valid,resp_error;
  wire [5:0] error;
  integer checks=0, cuts=0, bank_reads=0, stalls=0, live_changes=0, i,j,k;
  reg [236:0] expected;
  reg [255:0] padded;
  string scenario;
  LiveTop dut(.clock(clock),.reset(reset),.value(value),.live(live),
    .checkpoint_shell_ckpt_freeze(freeze),.checkpoint_shell_ckpt_bank(bank),
    .checkpoint_shell_ckpt_slot(slot),.checkpoint_shell_ckpt_address(address),
    .checkpoint_shell_ckpt_match(),.checkpoint_shell_ckpt_data(),
    .checkpoint_shell_ckpt_reset(bank_reset),.checkpoint_shell_ckpt_req_valid(req_valid),
    .checkpoint_shell_ckpt_req_ready(req_ready),.checkpoint_shell_ckpt_resp_valid(resp_valid),
    .checkpoint_shell_ckpt_resp_ready(resp_ready),.checkpoint_shell_ckpt_resp_data(response_data),
    .checkpoint_shell_ckpt_resp_error(resp_error),
    .checkpoint_shell_live_snapshot_reset(snapshot_reset),
    .checkpoint_shell_live_snapshot_request(request),.checkpoint_shell_live_snapshot_release(release_snapshot),
    .checkpoint_shell_live_snapshot_owners_present(owners_present),
    .checkpoint_shell_live_snapshot_owners_frozen(owners_frozen),
    .checkpoint_shell_live_snapshot_target_cycle(target_cycle),
    .checkpoint_shell_live_snapshot_word_address(word_address),
    .checkpoint_shell_live_snapshot_ready(ready),.checkpoint_shell_live_snapshot_valid(valid),
    .checkpoint_shell_live_snapshot_borrow_enable(borrow_enable),
    .checkpoint_shell_live_snapshot_failed(failed),.checkpoint_shell_live_snapshot_word_data(word_data),
    .checkpoint_shell_live_snapshot_word_error(word_error),.checkpoint_shell_live_snapshot_cut_cycle(cut_cycle),
    .checkpoint_shell_live_snapshot_error(error),.checkpoint_shell_live_snapshot_control_state(control_state));
  `include "bank-selector.svh"
  task check(input bit okay,input string signal_name);
    checks++;
    if(!okay)begin
      $display("LIVE_SHELL_DIVERGENCE scenario=%s cycle=%0d signal=%s reads=%0d pending=%b error=%h time=%0t",
        scenario,target_cycle,signal_name,bank_reads,dut.shell.checkpoint_shell_ckpt_pending,error,$time);
      checkpoint_widget_failed();$finish;
    end
  endtask
  function automatic [236:0] arithmetic(input integer n);
    arithmetic={1'(n),64'(n),32'(n),1'(n),9'(n),(65'h10000000000000003+65'(n)),64'(n),1'(n)};
  endfunction
  task initialize(input integer cut);
    @(negedge clock); reset=1;bank_reset=1;snapshot_reset=1;freeze=0;
    request=0;release_snapshot=0;req_valid=0;resp_ready=0;owners_present=1;owners_frozen=1;
    target_cycle=0;word_address=0;
    repeat(2) @(posedge clock);
    @(negedge clock);reset=0;bank_reset=0;snapshot_reset=0;
    for(i=0;i<cut;i++)begin @(posedge clock);@(negedge clock); end
    check(live===arithmetic(cut),"independent live arithmetic before cut");
    check(value===64'(cut),"independent functional arithmetic before cut");
    target_cycle=cut;freeze=1;
  endtask
  task capture;
    request=1;#1;
    check(ready&&!valid&&!req_ready&&!resp_valid,"no bank handshake on accepting edge");
    @(posedge clock);expected=arithmetic(integer'(target_cycle));padded={19'b0,expected};
    #1;request=0;#1;
    check(valid&&borrow_enable&&!failed&&cut_cycle==target_cycle,"complete common cut accepted");
    check(control_state[236:0]===expected&&control_state[237]===1'b1,"entire preedge payload");
    check(live!==expected,"original live owners keep executing at capture");
    cuts++;
  endtask
  task read_snapshot;
    for(j=0;j<4;j++)begin
      @(negedge clock);word_address=j;#1;
      check(valid&&!word_error&&word_data===padded[j*64+:64],"staged word and high padding");
      check(control_state[236:0]===expected,"immutable payload during live execution");
      if(live!==expected)live_changes++;
    end
    word_address=4;#1;check(word_error&&word_data===0&&valid&&!failed,"out of range word is contained");
    word_address=0;
  endtask
  task begin_bank;
    @(negedge clock);bank=COUNT_BANK;slot=COUNT_SLOT;address=0;req_valid=1;#1;
    check(req_ready&&borrow_enable,"staged bank request permitted");
    @(posedge clock);#1;req_valid=0;#1;
    check(resp_valid&&!resp_error&&response_data===target_cycle,"frozen original bank value");
    bank_reads++;
  endtask
  task expect_fault(input integer bit_index);
    #1;check(failed&&!valid&&!borrow_enable&&!req_ready&&!resp_valid&&word_error&&word_data===0,
      "fault revokes publication before acknowledgement");
    @(posedge clock);#1;
    check(error[bit_index],"sticky fault identity");
    check(value===target_cycle,"functional cut retained on failure");
  endtask
  initial begin
    $dumpfile("live-shell-snapshot.vcd");$dumpvars(0,live_shell_snapshot_tb);
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    if(scenario=="healthy"||scenario=="payload")begin
      for(k=0;k<4;k++)begin
        initialize(k==0?0:k==1?17:k==2?128:256);capture();read_snapshot();begin_bank();
        repeat(8)begin
          @(negedge clock);#1;
          check(resp_valid&&response_data===target_cycle&&!resp_error,"retained response under backpressure");
          check(value===target_cycle&&control_state[236:0]===expected,"functional hold and immutable live cut");
          stalls++;live_changes++;
        end
        @(negedge clock);resp_ready=1;@(posedge clock);#1;resp_ready=0;
        @(negedge clock);release_snapshot=1;#1;
        check(!valid&&!borrow_enable&&!req_ready&&!resp_valid,"release revokes permission before edge");
        @(posedge clock);#1;release_snapshot=0;freeze=0;target_cycle=target_cycle+1;
        @(posedge clock);#1;check(!failed&&value===target_cycle,"healthy functional release");
      end
      $display("LIVE_SHELL_SNAPSHOT_PASS checks=%0d cuts=%0d reads=%0d stalls=%0d live_changes=%0d",
        checks,cuts,bank_reads,stalls,live_changes);
    end else begin
      initialize(17);
      if(scenario=="missing-before")begin owners_present=0;request=1;expect_fault(0);end
      else if(scenario=="freeze-before")begin owners_frozen=0;request=1;expect_fault(1);end
      else if(scenario=="early-read")begin req_valid=1;expect_fault(3);end
      else if(scenario=="sameedge-read")begin request=1;req_valid=1;expect_fault(3);end
      else if(scenario=="overlap")begin request=1;release_snapshot=1;expect_fault(5);end
      else begin
        capture();
        if(scenario=="duplicate")begin request=1;expect_fault(5);end
        else if(scenario=="drift")begin target_cycle++;#1;check(failed&&!valid&&!req_ready,"immediate target drift");
          @(posedge clock);#1;target_cycle--;check(error[4]&&!valid,"drift retained");end
        else if(scenario=="missing-after")begin owners_present=0;expect_fault(0);end
        else if(scenario=="lost-freeze")begin freeze=0;expect_fault(1);end
        else if(scenario=="lost-owner-freeze")begin owners_frozen=0;expect_fault(1);end
        else if(scenario=="endpoint-reset")begin bank_reset=1;expect_fault(0);end
        else if(scenario=="busy-release")begin begin_bank();release_snapshot=1;expect_fault(2);
          check(dut.shell.checkpoint_shell_ckpt_pending,"unacknowledged response retained");end
        else begin check(0,"unknown scenario");end
        check(control_state[236:0]===expected&&control_state[237],"failed epoch retains staged bytes");
      end
      $display("LIVE_SHELL_SNAPSHOT_NEGATIVE_PASS scenario=%s checks=%0d",scenario,checks);
    end
    $finish;
  end
  initial begin #100000;$display("LIVE_SHELL_TIMEOUT");checkpoint_widget_failed();$finish;end
endmodule
