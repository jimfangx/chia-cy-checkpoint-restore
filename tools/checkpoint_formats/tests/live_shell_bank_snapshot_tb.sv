`timescale 1ns/1ps
module live_shell_snapshot_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=~clock;
  `include "native-geometry.svh"
  reg writeEn=0; reg [1:0] ramAddress=0; reg [63:0] ramData=0;
  wire [63:0] memoryOut;
  reg reset=1, freeze=0, bank_reset=1, request=0, release_snapshot=0, snapshot_reset=1;
  reg owners_present=1, owners_frozen=1, req_valid=0, resp_ready=0;
  reg [7:0] bank=0; reg [15:0] slot=0; reg [31:0] address=0, word_address=0;
  reg [63:0] target_cycle=0;
  wire [63:0] value, response_data, word_data, cut_cycle;
  wire [236:0] live;
  wire [BITS+70:0] control_state;
  wire ready,valid,borrow_enable,failed,word_error,req_ready,resp_valid,resp_error;
  wire [5:0] error;
  integer checks=0, cuts=0, bank_reads=0, stalls=0, live_changes=0, i,j,k,m;
  reg [63:0] frozenMemory;
  reg [BITS-1:0] expected;
  reg [WORDS*64-1:0] padded;
  string scenario;
  LiveTop dut(.clock(clock),.reset(reset),.value(value),.live(live),
    .writeEn(writeEn),.address(ramAddress),.data(ramData),.memoryOut(memoryOut),
    .checkpoint_shell_ckpt_native_state(),
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
  `include "native-probes.svh"
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
    @(negedge clock); reset=1;bank_reset=(cuts==0);snapshot_reset=(cuts==0);freeze=0;
    request=0;release_snapshot=0;req_valid=0;resp_ready=0;owners_present=1;owners_frozen=1;
    target_cycle=0;word_address=0;
    // Initialize actual memory bytes through original functional I/O. Keep the
    // independent snapshot and endpoint reset asserted until every implicit RAM
    // data/forwarding pipeline has executed known original inputs.
    repeat(2) @(posedge clock);
    for(m=0;m<4;m++)begin
      @(negedge clock);writeEn=1;ramAddress=2'(m);ramData=64'h12340000+64'(m);
      @(posedge clock);#1;
    end
    @(negedge clock);writeEn=0;ramAddress=0;
    repeat(3) @(posedge clock);
    @(negedge clock);reset=0;bank_reset=0;snapshot_reset=0;
    for(i=0;i<cut;i++)begin @(posedge clock);@(negedge clock); end
    check(live===arithmetic(cut),"independent live arithmetic before cut");
    check(value===64'(cut),"independent functional arithmetic before cut");
    target_cycle=cut;freeze=1;frozenMemory=memoryOut;
  endtask
  task capture;
    request=1;#1;
    check(ready&&!valid&&!req_ready&&!resp_valid,"no bank handshake on accepting edge");
    @(posedge clock);expected={native_probes,arithmetic(integer'(target_cycle))};padded=expected;
    #1;request=0;#1;
    check(valid&&borrow_enable&&!failed&&cut_cycle==target_cycle,"complete common cut accepted");
    check(control_state[BITS-1:0]===expected&&control_state[BITS]===1'b1,"entire preedge payload");
    if(cuts!=0)check(dut.shell.checkpoint_shell_ckpt_saved_data===64'h12340003,
      "nonzero inactive response bytes retained across released cuts");
    check(live!==expected[236:0],"original live owners keep executing at capture");
    cuts++;
  endtask
  task read_snapshot;
    for(j=0;j<WORDS;j++)begin
      @(negedge clock);word_address=j;#1;
      check(valid&&!word_error&&word_data===padded[j*64+:64],"staged word and high padding");
      check(control_state[BITS-1:0]===expected,"immutable payload during live execution");
      if(live!==expected[236:0])live_changes++;
    end
    word_address=WORDS;#1;check(word_error&&word_data===0&&valid&&!failed,"out of range word is contained");
    word_address=0;
  endtask
  task read_staged_bank;
    for(j=0;j<WORDS;j++)begin
      @(negedge clock);bank=SNAPSHOT_BANK;slot=0;address=j;req_valid=1;#1;
      check(req_ready,"staged payload bank ready");
      @(posedge clock);#1;req_valid=0;
      // Change public selectors while the response is pending. Routing must
      // retain its owner and bytes, including across arbitrary backpressure.
      bank=COUNT_BANK;slot=COUNT_SLOT;address=32'hffffffff;
      repeat(5)begin
        @(negedge clock);#1;
        check(resp_valid&&!resp_error&&response_data===padded[j*64+:64],"immutable staged bank response");
        check(!req_ready,"one outstanding response across both banks");
        check(control_state[BITS-1:0]===expected&&value===target_cycle,"same cut during staging readout");
      end
      resp_ready=1;@(posedge clock);#1;resp_ready=0;bank_reads++;
    end
    // Slot/address errors are explicit responses and leave the cut intact.
    for(j=0;j<2;j++)begin
      @(negedge clock);bank=SNAPSHOT_BANK;slot=j==0?1:0;address=j==0?0:WORDS;req_valid=1;#1;
      check(req_ready,"invalid staged selector accepted for error response");
      @(posedge clock);#1;req_valid=0;
      check(resp_valid&&resp_error&&response_data===0,"invalid staged selector rejected");
      resp_ready=1;@(posedge clock);#1;resp_ready=0;bank_reads++;
    end
  endtask
  task begin_bank;
    @(negedge clock);bank=COUNT_BANK;slot=COUNT_SLOT;address=0;req_valid=1;#1;
    check(req_ready&&borrow_enable,"staged bank request permitted");
    @(posedge clock);#1;req_valid=0;#1;
    while(!resp_valid)begin @(negedge clock);#1;end
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
        initialize(k==0?0:k==1?17:k==2?128:256);capture();read_snapshot();read_staged_bank();begin_bank();
        repeat(8)begin
          @(negedge clock);#1;
          check(resp_valid&&response_data===target_cycle&&!resp_error,"retained response under backpressure");
          check(value===target_cycle&&control_state[BITS-1:0]===expected,"functional hold and immutable live cut");
          stalls++;live_changes++;
        end
        @(negedge clock);resp_ready=1;@(posedge clock);#1;resp_ready=0;
        // Read the original synchronous RAM address pipeline as a separate
        // owner, proving every original descriptor survives shared routing.
        @(negedge clock);bank=PIPE_BANK;slot=PIPE_SLOT;address=0;req_valid=1;#1;
        check(req_ready,"original pipeline bank ready");
        @(posedge clock);#1;req_valid=0;
        while(!resp_valid)begin @(negedge clock);#1;end
        check(!resp_error&&response_data===0,"original frozen two-bit RAM address pipeline");
        resp_ready=1;@(posedge clock);#1;resp_ready=0;bank_reads++;
        // Read every original memory word through the real borrowed native
        // reader. The public functional output stays at its saved value while
        // reader phases and response bytes keep changing after the snapshot.
        for(m=0;m<4;m++)begin
          @(negedge clock);bank=MEM_BANK;slot=MEM_SLOT;address=m;req_valid=1;#1;
          check(req_ready,"native memory request ready");
          @(posedge clock);#1;req_valid=0;
          while(!resp_valid)begin @(negedge clock);#1;
            check(memoryOut===frozenMemory,"functional RAM output held during borrowed read");end
          check(!resp_error&&response_data===64'h12340000+64'(m),"complete original RAM bytes");
          check(control_state[BITS-1:0]===expected,"native reader staging immutable during borrow");
          repeat(3)begin @(negedge clock);#1;check(resp_valid,"native response stalled");end
          resp_ready=1;@(posedge clock);#1;resp_ready=0;bank_reads++;
        end
        read_snapshot();
        @(negedge clock);release_snapshot=1;#1;
        check(!valid&&!borrow_enable&&!req_ready&&!resp_valid,"release revokes permission before edge");
        @(posedge clock);#1;release_snapshot=0;freeze=0;target_cycle=target_cycle+1;
        @(posedge clock);#1;check(!failed&&value===target_cycle,"healthy functional release");
      end
      $display("LIVE_SHELL_SNAPSHOT_PASS checks=%0d cuts=%0d reads=%0d stalls=%0d live_changes=%0d",
        checks,cuts,bank_reads,stalls,live_changes);
    end else begin
      initialize(17);
      if(scenario=="busy-reader-capture")begin
        // Emulate an existing nonzero native-reader phase with no pending
        // response: pending alone is insufficient to certify an idle cut.
        force dut.shell.checkpoint_shell_ckpt_native_phase=2'd3;
        request=1;expect_fault(2);
        release dut.shell.checkpoint_shell_ckpt_native_phase;
      end
      else if(scenario=="missing-before")begin owners_present=0;request=1;expect_fault(0);end
      else if(scenario=="freeze-before")begin owners_frozen=0;request=1;expect_fault(1);end
      else if(scenario=="staged-early-read")begin bank=SNAPSHOT_BANK;req_valid=1;expect_fault(3);end
      else if(scenario=="staged-sameedge-read")begin bank=SNAPSHOT_BANK;request=1;req_valid=1;expect_fault(3);end
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
        else if(scenario=="busy-reader-release")begin
          @(negedge clock);bank=MEM_BANK;slot=MEM_SLOT;address=2;req_valid=1;
          @(posedge clock);#1;req_valid=0;release_snapshot=1;expect_fault(2);
        end
        else if(scenario=="staged-busy-release"||scenario=="staged-lost-freeze"||scenario=="staged-drift")begin
          @(negedge clock);bank=SNAPSHOT_BANK;slot=0;address=2;req_valid=1;
          @(posedge clock);#1;req_valid=0;
          check(resp_valid&&!resp_error,"staged response pending before fault");
          if(scenario=="staged-busy-release")begin release_snapshot=1;expect_fault(2);end
          else if(scenario=="staged-lost-freeze")begin freeze=0;expect_fault(1);end
          else begin target_cycle++;#1;check(failed&&!resp_valid&&!req_ready,"pending staged drift revokes permission");
            @(posedge clock);#1;target_cycle--;check(error[4],"pending staged drift retained");end
          check(dut.checkpoint_live_readout_adapter.pending&&dut.checkpoint_live_readout_adapter.snapshot_bank.pending,
            "failed epoch retains both unacknowledged readout owners");
        end
        else if(scenario=="busy-release")begin begin_bank();release_snapshot=1;expect_fault(2);
          check(dut.shell.checkpoint_shell_ckpt_pending,"unacknowledged response retained");end
        else begin check(0,"unknown scenario");end
        check(control_state[BITS-1:0]===expected&&control_state[BITS],"failed epoch retains staged bytes");
      end
      $display("LIVE_SHELL_SNAPSHOT_NEGATIVE_PASS scenario=%s checks=%0d",scenario,checks);
    end
    $finish;
  end
  initial begin #100000;$display("LIVE_SHELL_TIMEOUT");checkpoint_widget_failed();$finish;end
endmodule
