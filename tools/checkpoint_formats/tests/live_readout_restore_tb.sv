`timescale 1ns/1ps
`ifndef READOUT_BITS
`define READOUT_BITS 557
`endif
module live_readout_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=`READOUT_BITS;
  reg clock=0; always #5 clock=~clock;
  reg reset=0,permission=0,restore_hold=1,restore_load=0;
  reg [68:0] restore_state=0;
  wire restore_ready;
  reg [BITS-1:0] snapshot_state=0;
  reg request_valid=0,response_ready=0;
  reg [7:0] bank=1;reg [15:0] slot=0;reg [31:0] address=0;
  wire request_ready,response_valid,response_error,idle;
  wire [63:0] response_data;
  wire original_request_valid,original_response_ready;
  reg original_request_ready=1,original_response_valid=0,original_response_error=0;
  reg [63:0] original_response_data=64'hfedcba9876543210;
  wire [7:0] original_bank;wire [15:0] original_slot;wire [31:0] original_address;
  wire [68:0] control_state;
  CheckpointLiveShellSnapshotReadout #(.BITS(BITS),.SNAPSHOT_BANK(1),.RESTORE_ENABLE(1)) dut(.*);
  // Compatibility instance sees the same hostile restore controls. An explicit
  // disabled parameter must leave its ordinary readout protocol unchanged.
  wire [68:0] disabled_state;wire disabled_restore_ready,disabled_request_ready,disabled_response_valid;
  CheckpointLiveShellSnapshotReadout #(.BITS(BITS),.SNAPSHOT_BANK(1),.RESTORE_ENABLE(0)) disabled(
    .clock(clock),.reset(reset),.permission(permission),.restore_hold(restore_hold),
    .restore_load(restore_load),.restore_state(restore_state),.restore_ready(disabled_restore_ready),
    .snapshot_state(snapshot_state),.request_valid(1'b0),.response_ready(1'b0),
    .bank(bank),.slot(slot),.address(address),.request_ready(disabled_request_ready),
    .response_valid(disabled_response_valid),.response_data(),.response_error(),
    .original_request_valid(),.original_request_ready(1'b1),.original_bank(),.original_slot(),.original_address(),
    .original_response_valid(1'b0),.original_response_ready(),.original_response_data(64'b0),
    .original_response_error(1'b0),.idle(),.control_state(disabled_state));
  reg [68:0] image[0:0],expected,before_state;
  reg [63:0] expected_data;
  reg expected_error;
  integer checks=0,acks=0,loads=0,fd;
  string mode,cut,scenario,image_path;
  task check(input bit ok,input string why);
    checks++;
    if(!ok)begin
      $display("READOUT_RESTORE_DIVERGENCE signal=%s bits=%0d cut=%s case=%s ack=%0d loads=%0d",why,BITS,cut,scenario,acks,loads);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task neg;@(negedge clock);#1;endtask
  task edge_done;@(posedge clock);#1;endtask
  task no_handshake;
    check(!request_ready&&!response_valid&&!original_request_valid&&!original_response_ready&&!idle,
      "parked-no-handshake");
  endtask
  task independent_readback(input [68:0] value);
    check(control_state===value,"complete-control-before-ack");
    check(dut.pending===value[0]&&dut.snapshot_owner===value[1]&&
      dut.snapshot_bank.saved_data===value[65:2]&&dut.snapshot_bank.saved_error===value[66]&&
      dut.snapshot_bank.pending===value[67]&&dut.snapshot_bank.failed===value[68],"all-independent-register-fields");
  endtask
  task load(input [68:0] value);
    neg();restore_state=value;restore_load=1;#1;
    check(restore_ready,"load-ready");no_handshake();
    edge_done();loads++;restore_load=0;independent_readback(value);
  endtask
  initial begin
    $dumpfile("live-readout-restore.vcd");$dumpvars(0,live_readout_restore_tb);
    check($value$plusargs("MODE=%s",mode),"mode-required");
    check($value$plusargs("CUT=%s",cut),"cut-required");
    check($value$plusargs("IMAGE=%s",image_path),"image-required");
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    for(integer b=0;b<BITS;b++)snapshot_state[b]=((b*17+3)%23)<11;
    if(mode=="donor")begin
      restore_hold=0;reset=1;repeat(2)edge_done();neg();reset=0;permission=1;
      if(cut!="empty")begin
        bank=cut=="original"?0:1;slot=cut=="error"?1:0;request_valid=1;#1;
        check(request_ready,"donor-request-ready");edge_done();request_valid=0;
        if(cut=="original")original_response_valid=1;
        #1;check(response_valid,"donor-response-owned");
        if(cut=="released")begin response_ready=1;edge_done();response_ready=0;end
        if(cut=="fault")begin neg();permission=0;edge_done();check(dut.snapshot_bank.failed,"donor-lost-cut-sticky");end
      end
      fd=$fopen(image_path,"w");check(fd!=0,"image-open");
      $fdisplay(fd,"%h",control_state);$fclose(fd);
      $display("READOUT_DONOR_PASS bits=%0d cut=%s checks=%0d",BITS,cut,checks);$finish;
    end
    check(mode=="restore","known-mode");
    // No reset or hierarchical initialization of the destination. A new VCS
    // process loads only via synthesized ports before any bank acknowledgement.
    $readmemh(image_path,image);expected=image[0];load(expected);
    repeat(8)begin neg();snapshot_state=~snapshot_state;bank=bank^8'hff;slot++;address++;
      edge_done();no_handshake();independent_readback(expected);end
    if(scenario=="bits")begin
      for(integer b=0;b<69;b++)begin
        for(integer polarity=0;polarity<2;polarity++)begin
          expected=0;expected[b]=1;
          if(b==67)begin expected[0]=1;expected[1]=1;end
          if(polarity)begin
            expected='1;expected[b]=0;
            if(b==0||b==1)expected[67]=0;
            if(b==67)expected[0]=0;
          end
          load(expected);
        end
      end
      // The compatibility instance is reset only AFTER the fresh-restore proof.
      neg();reset=1;restore_load=1;restore_state='1;#1;
      check(!restore_ready,"reset-rejects-load");edge_done();
      check(control_state===0&&disabled_state===0,"reset-over-entire-owner");
      neg();reset=0;permission=1;
      #1;check(!disabled_restore_ready&&disabled_request_ready&&!disabled_response_valid,"default-restore-disabled");
      repeat(4)begin edge_done();check(disabled_state===0,"disabled-load-cannot-change-state");end
      $display("READOUT_BITS_PASS bits=%0d owner_bits=69 loads=%0d checks=%0d ack=0",BITS,loads,checks);$finish;
    end
    if(scenario!="healthy")begin
      before_state=control_state;neg();restore_state=~expected;restore_load=1;
      // Keep shape valid except in the two deliberate semantic shape faults.
      restore_state[67]=restore_state[0]&&restore_state[1];
      case(scenario)
        "permission":permission=1;
        "request":request_valid=1;
        "response":response_ready=1;
        "unheld":restore_hold=0;
        "orphan":begin restore_state[67]=1;restore_state[0]=0;end
        "lost":begin restore_state[0]=1;restore_state[1]=1;restore_state[67]=0;end
        default:check(0,"known-negative");
      endcase
      #1;check(!restore_ready,"unsafe-load-rejected");no_handshake();edge_done();
      // Rejected routing loads cannot overwrite any donor byte or route.
      // Unheld load loses permission on a pending snapshot and can set only
      // its existing sticky failure bit; it may never partially load data.
      check(control_state[67:0]===before_state[67:0],"unsafe-no-partial-load");
      if(scenario!="unheld")check(control_state===before_state,"unsafe-retains-whole-owner");
      neg();permission=0;request_valid=0;response_ready=0;restore_hold=1;restore_load=0;
      load(image[0]);
      $display("READOUT_NEGATIVE_PASS bits=%0d case=%s checks=%0d ack=0",BITS,scenario,checks);$finish;
    end
    // Resume component transport after complete independent readback. The
    // original endpoint environment is a separate directed fixture, not a DUT
    // restore or a target environment. Change all public selectors while the
    // pending route drains to verify retained routing rather than re-decoding.
    neg();permission=1;restore_hold=0;bank=8'hff;slot=16'hffff;address=32'hffffffff;
    original_response_valid=cut=="original";
    expected_data=cut=="original"?64'hfedcba9876543210:image[0][65:2];
    expected_error=cut=="original"?0:image[0][66];
    if(image[0][68])begin
      #1;check(!response_valid&&!request_ready,"restored-error-remains-closed");
      repeat(8)begin edge_done();independent_readback(image[0]);end
      neg();reset=1;edge_done();neg();reset=0;
    end else if(image[0][0])begin
      repeat(16)begin #1;check(response_valid&&response_data===expected_data&&response_error===expected_error,
        "retained-response-before-ack");check(!request_ready,"pending-blocks-overlap");edge_done();end
      neg();response_ready=1;#1;check(response_valid,"exactly-one-restored-ack");
      edge_done();acks++;response_ready=0;original_response_valid=0;
    end
    // Continue beyond the restored response with 128 new bank requests,
    // alternating actual snapshot reads and a separate original-bank peer.
    for(integer t=0;t<128;t++)begin
      neg();bank=t%2;slot=0;address=0;request_valid=1;
      expected_data=bank==1?64'(snapshot_state):original_response_data;
      #1;check(request_ready,"continued-request-ready");edge_done();request_valid=0;
      original_response_valid=bank==0;
      // Change selectors immediately; only the saved route may own the ack.
      bank=bank^8'hff;
      repeat(3)begin #1;check(response_valid&&!response_error&&response_data===expected_data,"continued-response");edge_done();end
      neg();response_ready=1;edge_done();acks++;response_ready=0;original_response_valid=0;
    end
    $display("READOUT_RESTORE_PASS bits=%0d cut=%s checks=%0d loads=%0d ack=%0d continuation=128 target_edges=0",BITS,cut,checks,loads,acks);$finish;
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
