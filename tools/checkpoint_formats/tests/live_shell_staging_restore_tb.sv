`timescale 1ns/1ps
module live_shell_staging_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=`STAGING_BITS, OWNER_BITS=BITS+71, WORDS=(BITS+63)/64;
  reg clock=0;always #5 clock=~clock;
  reg reset=1,bank_reset=1,snapshot_reset=0,freeze=1;
  reg restore_hold=1,restore_load=0,request=0,release_snapshot=0,owners_present=1,owners_frozen=1;
  reg req_valid=0,resp_ready=0;
  reg [OWNER_BITS-1:0] restore_state=0;
  reg [63:0] target_cycle=0;
  reg [31:0] word_address=0,address=0;
  reg [7:0] bank=0;reg [15:0] slot=0;
  wire [OWNER_BITS-1:0] control_state;
  wire restore_ready,valid,borrow_enable,ready,failed,word_error,req_ready,resp_valid;
  wire [63:0] word_data,value,cut_cycle;
  wire [5:0] error;
`ifdef NATIVE_STAGING
  reg writeEn=0;reg [1:0] ramAddress=0;reg [63:0] ramData=0;
`endif
  integer checks=0,loads=0,reads=0,fd,i;
  string mode,scenario,image,cut;
  reg [OWNER_BITS-1:0] donor,row,previous;
  reg [WORDS*64-1:0] padded;
  LiveTop dut(.clock(clock),.reset(reset),.value(value),.live(),
`ifdef NATIVE_STAGING
    .writeEn(writeEn),.address(ramAddress),.data(ramData),.memoryOut(),
`endif
    .checkpoint_shell_ckpt_freeze(freeze),.checkpoint_shell_ckpt_reset(bank_reset),
    .checkpoint_shell_ckpt_bank(bank),.checkpoint_shell_ckpt_slot(slot),.checkpoint_shell_ckpt_address(address),
    .checkpoint_shell_ckpt_req_valid(req_valid),.checkpoint_shell_ckpt_resp_ready(resp_ready),
    .checkpoint_shell_ckpt_req_ready(req_ready),.checkpoint_shell_ckpt_resp_valid(resp_valid),
    .checkpoint_shell_live_snapshot_reset(snapshot_reset),.checkpoint_shell_live_snapshot_request(request),
    .checkpoint_shell_live_snapshot_release(release_snapshot),
    .checkpoint_shell_live_snapshot_owners_present(owners_present),.checkpoint_shell_live_snapshot_owners_frozen(owners_frozen),
    .checkpoint_shell_live_snapshot_target_cycle(target_cycle),.checkpoint_shell_live_snapshot_word_address(word_address),
    .checkpoint_shell_live_snapshot_ready(ready),.checkpoint_shell_live_snapshot_valid(valid),
    .checkpoint_shell_live_snapshot_borrow_enable(borrow_enable),.checkpoint_shell_live_snapshot_failed(failed),
    .checkpoint_shell_live_snapshot_word_data(word_data),.checkpoint_shell_live_snapshot_word_error(word_error),
    .checkpoint_shell_live_snapshot_cut_cycle(cut_cycle),.checkpoint_shell_live_snapshot_error(error),
    .checkpoint_shell_live_snapshot_control_state(control_state),
    .checkpoint_shell_live_snapshot_restore_hold(restore_hold),.checkpoint_shell_live_snapshot_restore_load(restore_load),
    .checkpoint_shell_live_snapshot_restore_state(restore_state),.checkpoint_shell_live_snapshot_restore_ready(restore_ready));
  task check(input bit ok,input string signal_name);
    checks++;
    if(!ok)begin
      $display("STAGING_RESTORE_DIVERGENCE signal=%s bits=%0d mode=%s case=%s loads=%0d reads=%0d time=%0t",signal_name,BITS,mode,scenario,loads,reads,$time);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task compare(input [OWNER_BITS-1:0] expected);
    check(control_state===expected,"complete-control-before-ack");
    check(dut.shell.checkpoint_shell_live_snapshot_adapter.payload===expected[BITS-1:0] &&
      dut.shell.checkpoint_shell_live_snapshot_adapter.occupied===expected[BITS] &&
      dut.shell.checkpoint_shell_live_snapshot_adapter.cut_cycle===expected[BITS+64:BITS+1] &&
      dut.shell.checkpoint_shell_live_snapshot_adapter.error===expected[BITS+70:BITS+65],"independent-four-original-registers");
  endtask
  task load(input [OWNER_BITS-1:0] next);
    @(negedge clock);restore_hold=1;restore_state=next;restore_load=1;#1;
    check(restore_ready&&!valid&&!borrow_enable&&!req_ready&&!resp_valid,"qualified-load-no-handshake");
    @(posedge clock);#1;loads++;restore_load=0;compare(next);
    repeat(8)begin @(posedge clock);#1;compare(next);
      check(!valid&&!borrow_enable&&!req_ready&&!resp_valid&&dut.shell.checkpoint_shell_live_snapshot_functional_hold,
        "held-quiet-even-empty-donor");end
  endtask
  initial begin
    $dumpfile("staging-restore.vcd");$dumpvars(0,live_shell_staging_restore_tb);
    if(!$value$plusargs("MODE=%s",mode))mode="restore";
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    if(!$value$plusargs("CUT=%s",cut))cut="occupied";
    check($value$plusargs("IMAGE=%s",image),"image-required");
    if(mode=="donor")begin
      restore_hold=0;snapshot_reset=1;freeze=0;
      repeat(3)@(posedge clock);
`ifdef NATIVE_STAGING
      for(i=0;i<4;i++)begin @(negedge clock);writeEn=1;ramAddress=2'(i);ramData=64'h98760000+64'(i);@(posedge clock);end
      @(negedge clock);writeEn=0;repeat(3)@(posedge clock);
`endif
      @(negedge clock);reset=0;bank_reset=0;snapshot_reset=0;
      repeat(17)begin @(posedge clock);@(negedge clock);end
      target_cycle=17;freeze=1;
      if(cut!="empty")begin
        request=1;#1;check(ready,"donor-request-ready");@(posedge clock);#1;request=0;#1;
        check(valid&&!failed,"donor-captured");
        if(cut=="released")begin @(negedge clock);release_snapshot=1;@(posedge clock);#1;release_snapshot=0;end
        if(cut=="error")begin @(negedge clock);owners_present=0;@(posedge clock);#1;owners_present=1;check(error[0],"donor-sticky-error");end
      end
      @(negedge clock);donor=control_state;
      check(!$isunknown(donor),"known-complete-donor");compare(donor);
      fd=$fopen(image,"w");check(fd!=0,"image-open");$fdisplay(fd,"%h",donor);$fclose(fd);
      $display("STAGING_DONOR_PASS bits=%0d cut=%s owner_bits=%0d",BITS,cut,OWNER_BITS);
    end else begin
      // No destination staging reset, request or target/bank edge initializes
      // this owner. Bank-controller reset only initializes the separate reader.
      repeat(3)@(posedge clock);@(negedge clock);bank_reset=0;reset=0;
      fd=$fopen(image,"r");check(fd!=0,"image-open");check($fscanf(fd,"%h",donor)==1,"image-read");$fclose(fd);
      target_cycle=donor[BITS+64:BITS+1];load(donor);
      if(scenario=="bits")begin
        for(i=0;i<OWNER_BITS;i++)begin row=0;row[i]=1;load(row);row='1;row[i]=0;load(row);end
        load(donor);
      end else if(scenario!="healthy")begin
        @(negedge clock);previous=control_state;restore_load=1;restore_state=~donor;
        if(scenario=="missing-owner")owners_present=0;
        else if(scenario=="lost-freeze")owners_frozen=0;
        else if(scenario=="bank-reset")bank_reset=1;
        else if(scenario=="request")request=1;
        else if(scenario=="release")release_snapshot=1;
        else if(scenario=="borrow")req_valid=1;
        else if(scenario=="unheld")restore_hold=0;
        else if(scenario=="busy")begin
          restore_load=0;restore_hold=0;req_valid=1;#1;check(req_ready,"start-real-busy-reader");
          @(posedge clock);#1;req_valid=0;@(negedge clock);restore_hold=1;restore_load=1;
        end else check(0,"unknown-negative");
        #1;check(!restore_ready&&!req_ready&&!resp_valid,"unsafe-before-load");
        @(posedge clock);#1;restore_load=0;
        check(control_state[BITS+64:0]===previous[BITS+64:0],"rejected-payload-cycle-occupied-unchanged");
        check(error!=0,"unsafe-sticky-error");
        $display("STAGING_NEGATIVE_PASS bits=%0d case=%s loads=%0d reads=%0d",BITS,scenario,loads,reads);$finish;
      end
      // Every staged byte, high padding, inactive payload and sticky donor
      // error has been read back before local permission can be released.
      if(!donor[OWNER_BITS-1:BITS+65]&&donor[BITS])begin
        @(negedge clock);restore_hold=0;#1;check(valid&&borrow_enable&&!failed,"qualified-release");
        padded=donor[BITS-1:0];
        for(i=0;i<WORDS;i++)begin
          @(negedge clock);word_address=i;#1;check(!word_error&&word_data===padded[i*64+:64],"restored-word");reads++;
          @(posedge clock);#1;compare(donor);
        end
        repeat(128)begin @(posedge clock);#1;compare(donor);check(valid&&!failed,"sustained-staging-continuation");end
      end
      $display("STAGING_RESTORE_PASS bits=%0d case=%s cut=%s loads=%0d reads=%0d",BITS,scenario,cut,loads,reads);
    end
    $finish;
  end
  initial begin #2000000;check(0,"watchdog");end
endmodule
