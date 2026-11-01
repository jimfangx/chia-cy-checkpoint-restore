`timescale 1ns/1ps
// Exercise the ACTUAL emitted wrapper with an occupied staging owner. There
// are no force/backdoor assignments or invented restore images in this test.
module live_readout_permission_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  `include "permission-geometry.svh"
  reg clock=0; always #5 clock=~clock;
  reg reset=1, bank_reset=1, snapshot_reset=1, freeze=0;
  reg request=0, release_snapshot=0, owners_present=1, owners_frozen=1;
  reg writeEn=0; reg [1:0] ram_address=0; reg [63:0] ram_data=0;
  reg request_valid=0,response_ready=0,capture_hold=0;
  reg [7:0] bank=0; reg [15:0] slot=0; reg [31:0] address=0,capture_address=0;
  reg [63:0] target_cycle=17;
  wire request_ready,response_valid,response_error,borrow_enable,failed,stage_valid;
  wire [63:0] response_data,capture_data,value;
  wire capture_valid,capture_error;
  wire [68:0] control_state;
  wire [BITS+70:0] staging_state;
  wire permission=dut.checkpoint_live_readout_adapter.permission;
  wire original_request_valid=dut.checkpoint_live_readout_adapter.original_request_valid;
  wire original_response_ready=dut.checkpoint_live_readout_adapter.original_response_ready;
  wire restore_hold=0,restore_load=0;
  wire restore_ready=dut.checkpoint_live_readout_adapter.restore_ready;
  wire [5:0] staging_error;
  reg [68:0] held_owner;
  reg [BITS+70:0] held_stage;
  reg [63:0] held_value,expected_response;
  integer checks=0, captures=0, acknowledgements=0, accepted=0, cut=17;
  string scenario;
  LiveTop dut(.clock(clock),.reset(reset),.value(value),.live(),.memoryOut(),
    .writeEn(writeEn),.address(ram_address),.data(ram_data),
    .checkpoint_shell_ckpt_freeze(freeze),.checkpoint_shell_ckpt_reset(bank_reset),
    .checkpoint_shell_ckpt_bank(bank),.checkpoint_shell_ckpt_slot(slot),.checkpoint_shell_ckpt_address(address),
    .checkpoint_shell_ckpt_req_valid(request_valid),.checkpoint_shell_ckpt_req_ready(request_ready),
    .checkpoint_shell_ckpt_resp_ready(response_ready),.checkpoint_shell_ckpt_resp_valid(response_valid),
    .checkpoint_shell_ckpt_resp_data(response_data),.checkpoint_shell_ckpt_resp_error(response_error),
    .checkpoint_shell_live_snapshot_reset(snapshot_reset),.checkpoint_shell_live_snapshot_request(request),
    .checkpoint_shell_live_snapshot_release(release_snapshot),
    .checkpoint_shell_live_snapshot_owners_present(owners_present),
    .checkpoint_shell_live_snapshot_owners_frozen(owners_frozen),
    .checkpoint_shell_live_snapshot_target_cycle(target_cycle),.checkpoint_shell_live_snapshot_word_address(32'b0),
    .checkpoint_shell_live_snapshot_borrow_enable(borrow_enable),.checkpoint_shell_live_snapshot_valid(stage_valid),
    .checkpoint_shell_live_snapshot_failed(failed),.checkpoint_shell_live_snapshot_error(staging_error),
    .checkpoint_shell_live_snapshot_control_state(staging_state),
`ifdef READOUT_PAIRED
    .checkpoint_live_readout_restore_hold(restore_hold),.checkpoint_live_readout_restore_load(restore_load),
    .checkpoint_live_readout_restore_state(69'b0),
`endif
    .checkpoint_live_readout_capture_hold(capture_hold),.checkpoint_live_readout_capture_address(capture_address),
    .checkpoint_live_readout_capture_valid(capture_valid),.checkpoint_live_readout_capture_data(capture_data),
    .checkpoint_live_readout_capture_error(capture_error),.checkpoint_live_readout_control_state(control_state));
  task check(input bit ok,input string why);
    checks++;
    if(!ok)begin
      $display("LIVE_PERMISSION_DIVERGENCE signal=%s scenario=%s cut=%0d captures=%0d accepted=%0d ack=%0d checks=%0d",
        why,scenario,target_cycle,captures,accepted,acknowledgements,checks);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task begin_read(input [7:0] b,input [15:0] s,input [31:0] a);
    @(negedge clock);bank=b;slot=s;address=a;request_valid=1;#1;
    check(request_ready&&permission&&borrow_enable&&!failed,"qualified-request");
    @(posedge clock);#1;accepted++;request_valid=0;
  endtask
  task finish_read;
    while(!response_valid)begin @(negedge clock);#1;end
    check(!response_error&&response_data===expected_response,"same-response-after-hold");
    // Public selectors may change while ownership stays with this response.
    bank=8'hfe;slot=16'hffff;address=32'hffffffff;
    repeat(5)begin @(negedge clock);#1;
      check(response_valid&&!response_error&&response_data===expected_response&&!failed,"resumed-backpressure");end
    response_ready=1;@(posedge clock);#1;acknowledgements++;response_ready=0;
    check(!control_state[0]&&!failed,"exactly-one-response-retired");
  endtask
  task park;
    @(negedge clock);held_owner=control_state;held_stage=staging_state;held_value=value;
    capture_hold=1;capture_address=0;#1;
    check(borrow_enable&&stage_valid&&!failed&&!permission,"local-revocation-preserves-staging-permission");
    for(integer word=0;word<8;word++)begin
      capture_address=word%2;#1;
      check(capture_valid&&!capture_error&&!request_ready&&!response_valid&&!restore_ready&&
        !original_request_valid&&!original_response_ready,"qualified-local-capture");
      check(capture_data===(capture_address==0?held_owner[63:0]:{59'b0,held_owner[68:64]}),
        "complete-capture-word-before-edge");
      @(posedge clock);#1;
      check(control_state===held_owner&&staging_state===held_stage&&value===held_value&&
        borrow_enable&&!failed,"owner-and-staging-retained");
      @(negedge clock);
    end
    capture_address=2;#1;
    check(capture_valid&&capture_error&&capture_data===0,"invalid-address-contained");
    @(posedge clock);#1;
    check(control_state===held_owner&&staging_state===held_stage&&!failed,"invalid-address-no-state-change");
    @(negedge clock);capture_address=0;captures++;
  endtask
  task unpark;
    capture_hold=0;#1;
    check(permission&&borrow_enable&&!failed&&!capture_valid&&!capture_error,"direct-permission-handoff");
  endtask
  initial begin
    $dumpfile("live-readout-permission.vcd");$dumpvars(0,live_readout_permission_tb);
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    if(!$value$plusargs("CUT=%d",cut))cut=17;
    target_cycle=64'(cut);
    repeat(2)@(posedge clock);
    for(integer word=0;word<4;word++)begin
      @(negedge clock);writeEn=1;ram_address=2'(word);ram_data=64'h12340000+64'(word);
      @(posedge clock);#1;
    end
    @(negedge clock);writeEn=0;ram_address=0;
    repeat(3)@(posedge clock);
    @(negedge clock);reset=0;bank_reset=0;snapshot_reset=0;
    for(integer n=0;n<cut;n++)begin @(posedge clock);@(negedge clock);end
    freeze=1;request=1;
    @(posedge clock);#1;request=0;#1;
    check(stage_valid&&borrow_enable&&!failed&&value===target_cycle,"live-staging-accepted");
    if(scenario=="healthy")begin
      park();unpark();
      for(integer word=0;word<WORDS;word++)begin
        expected_response=64'(staging_state[BITS-1:0]>>(64*word));
        begin_read(SNAPSHOT_BANK,0,word);park();unpark();finish_read();
      end
      expected_response=target_cycle;
      begin_read(COUNT_BANK,COUNT_SLOT,0);park();unpark();finish_read();
      for(integer word=0;word<4;word++)begin
        expected_response=64'h12340000+64'(word);
        // Capture immediately after admission, with the real native memory
        // reader still in flight, then again after its response settles.
        begin_read(MEM_BANK,MEM_SLOT,word);park();unpark();
        while(!response_valid)begin @(negedge clock);#1;end
        park();unpark();finish_read();
      end
      @(negedge clock);release_snapshot=1;#1;
      check(!permission&&!borrow_enable&&!failed,"idle-release-revokes-permission");
      @(posedge clock);#1;release_snapshot=0;freeze=0;target_cycle++;
      @(posedge clock);#1;check(!failed&&value===target_cycle,"normal-functional-resume");
      check(accepted==WORDS+5&&acknowledgements==accepted&&captures==WORDS+10,"complete-transaction-coverage");
      $display("LIVE_PERMISSION_PASS checks=%0d captures=%0d accepted=%0d ack=%0d",checks,captures,accepted,acknowledgements);
    end else begin
      expected_response=64'(staging_state[BITS-1:0]);begin_read(SNAPSHOT_BANK,0,0);park();
      if(scenario=="request"||scenario=="response")begin
        if(scenario=="request")request_valid=1;else response_ready=1;
        repeat(3)begin #1;
          check(!capture_valid&&capture_error&&capture_data===0&&!request_ready&&!response_valid&&
            !original_request_valid&&!original_response_ready,"unsafe-intent-rejected-before-edge");
          @(posedge clock);#1;
          check(control_state===held_owner&&staging_state===held_stage&&!failed,"unsafe-intent-retains-pending-state");
          @(negedge clock);
        end
        request_valid=0;response_ready=0;#1;check(capture_valid&&!capture_error,"safe-capture-recovers");
        unpark();finish_read();
      end else begin
        if(scenario=="release")release_snapshot=1;
        else if(scenario=="drift")target_cycle++;
        else if(scenario=="owner")owners_present=0;
        else if(scenario=="freeze")owners_frozen=0;
        else check(0,"unknown-case");
        #1;check(failed&&!borrow_enable&&!permission&&!request_ready&&!response_valid,"global-fault-revokes-publication");
        @(posedge clock);#1;
        @(negedge clock);release_snapshot=0;target_cycle=64'(cut);owners_present=1;owners_frozen=1;capture_hold=0;
        repeat(3)begin @(posedge clock);#1;
          check(failed&&!permission&&!request_ready&&!response_valid&&control_state[0]&&
            control_state[67]&&staging_state[BITS-1:0]===held_stage[BITS-1:0],"failed-cut-retains-unacknowledged-owners");
        end
        check(acknowledgements==0,"failed-cut-never-acknowledged");
      end
      $display("LIVE_PERMISSION_NEGATIVE_PASS scenario=%s checks=%0d captures=%0d accepted=%0d ack=%0d",
        scenario,checks,captures,accepted,acknowledgements);
    end
    $finish;
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
