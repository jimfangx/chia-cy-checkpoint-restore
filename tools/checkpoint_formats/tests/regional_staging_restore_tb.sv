`timescale 1ns/1ps
// All data expectations use independent arithmetic/memory, never state backdoors.
module regional_staging_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=!clock;
  reg reset=1, capture_reset=1, freeze_request=0, owner_present=1, write=0;
  // Explicit test-only perturbation of the collector input, never functional state.
  reg [63:0] cut_cycle_xor=0;
  reg [1:0] enable=3;
  reg [2:0] address=0;
  reg [129:0] data=0;
  wire [64:0] left_count, right_count, other_left_count, other_right_count;
  wire [63:0] cycle, other_cycle, host_ticks_out, control_ticks_out;
  wire [129:0] read_data, other_read_data;
  wire capture_clock_mask, capture_read_enable, failed;
  wire [3:0] capture_logical_ce, capture_captured_ce;
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
  reg snapshot_request=0, snapshot_release=0;
  reg [31:0] snapshot_word_address=0;
  wire snapshot_ready, snapshot_valid, snapshot_failed, snapshot_word_error;
  wire [63:0] snapshot_word_data, snapshot_cut_cycle;
  wire [5:0] snapshot_error;
  wire [`CONTROL_BITS-1:0] captured_control_state;
  wire [`CONTROL_BITS+70:0] staging_control_state;
  wire physical_read_enable;
  reg [`CONTROL_BITS-1:0] expected_control;
  integer snapshot_words=0;
  bit corrupt_snapshot;
  string snapshot_fault;
  reg restore_hold=0,restore_load=0;
  reg [`CONTROL_BITS+70:0] restore_state=0;
  wire restore_ready;
`ifdef WITH_ROUTERS
  wire [6:0] capture_router_state;
`endif
  NativeRegionsFixture dut(.*);
  // Aliases retain the original owner checker ABI.
  wire valid=snapshot_valid,borrow_enable=dut.host.checkpoint_region_cut_snapshot.staging.borrow_enable;
  wire request_ready=snapshot_ready,word_error=snapshot_word_error;
  wire [63:0] word_data=snapshot_word_data;
  wire [`CONTROL_BITS+70:0] control_state=staging_control_state;
  localparam integer BITS=`CONTROL_BITS,OWNER_BITS=BITS+71,WORDS=(BITS+63)/64;
  integer fd,i,checks=0,loads=0,requests=0,responses=0;
  string mode,scenario,image,cut;
  reg [OWNER_BITS-1:0] donor,row,previous;
  reg [BITS-1:0] expected_payload;
  reg [WORDS*64-1:0] padded;
  always @(posedge clock) begin
    if(!capture_reset) begin
      if(capture_request_valid&&capture_request_ready)requests++;
      if(capture_response_valid&&capture_response_ready)responses++;
    end
  end
  task check(input bit ok,input string signal_name);
    checks++;
    if(!ok)begin
      $display("REGIONAL_STAGING_FIRST_DIVERGENCE signal=%s cut=%0d case=%s loads=%0d acknowledged_requests=%0d acknowledged_responses=%0d",
        signal_name,cycle,scenario,loads,requests,responses);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task compare(input [OWNER_BITS-1:0] expected);
    check(control_state===expected,"complete-owner-before-ack");
    check(dut.host.checkpoint_region_cut_snapshot.staging.payload===expected[BITS-1:0]&&
      dut.host.checkpoint_region_cut_snapshot.staging.occupied===expected[BITS]&&
      dut.host.checkpoint_region_cut_snapshot.staging.cut_cycle===expected[BITS+64:BITS+1]&&
      dut.host.checkpoint_region_cut_snapshot.staging.error===expected[BITS+70:BITS+65],"four-original-registers");
  endtask
  task load(input [OWNER_BITS-1:0] next);
    @(negedge clock);#1;restore_hold=1;restore_load=1;restore_state=next;#1;
    check(restore_ready&&!snapshot_valid&&!capture_request_ready&&!capture_response_valid&&capture_clock_mask,
      "qualified-load-revokes-handshakes");
    @(posedge clock);#1;loads++;restore_load=0;#1;compare(next);
    // Hold must retain the actual common cut even for an empty/released donor
    // after the host withdraws its request. Occupancy cannot supply that hold.
    freeze_request=0;#1;
    repeat(8)begin @(posedge clock);#1;compare(next);
      check(capture_clock_mask&&cycle==38&&other_cycle==38&&
        !snapshot_valid&&!capture_request_ready&&!capture_response_valid,
        "held-empty-or-occupied-owner-keeps-cut");end
    freeze_request=1;#1;
  endtask
  initial begin
    $dumpfile("regional-staging-restore.vcd");$dumpvars(0,regional_staging_restore_tb);
    if(!$value$plusargs("MODE=%s",mode))mode="restore";
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    if(!$value$plusargs("CUT=%s",cut))cut="occupied";
    check($value$plusargs("IMAGE=%s",image),"image-required");
    // Original endpoints/controller are prepared with public inputs in each
    // fresh process. Only the staging owner is migrated by this regression.
    // Match the retained native-primitive fixture's GSR settling contract and
    // reset both complementary regional CE groups before counting target time.
    repeat(14)@(negedge clock);#1;enable=0;
    repeat(3)@(negedge clock);#1;enable=3;reset=0;capture_reset=0;
    repeat(38)@(posedge clock);
    #2;freeze_request=1;
    @(negedge clock);#1;check(capture_clock_mask,"common-low-phase-cut");
    @(posedge clock);#2;check(cycle==38&&physical_read_enable&&!failed,"independent-target-cut");
    expected_payload={{(BITS-75){1'b0}},1'b0,3'b000,64'd38,4'b0011,3'b011};
    if(mode=="donor")begin
      if(cut!="empty")begin
        @(negedge clock);#1;snapshot_request=1;
        @(posedge clock);#1;snapshot_request=0;#1;
        check(snapshot_valid&&!snapshot_failed,"source-capture");
        compare({6'b0,64'd38,1'b1,expected_payload});
        if(cut=="released")begin
          @(negedge clock);#1;snapshot_release=1;
          @(posedge clock);#1;snapshot_release=0;#1;
        end else if(cut=="error")begin
          @(negedge clock);#1;snapshot_request=1;
          @(posedge clock);#1;snapshot_request=0;#1;
          check(snapshot_error==6'b100000,"source-sticky-error");
        end
      end
      donor=control_state;
      if(cut=="empty")check(donor==0,"empty-source-owner");
      if(cut=="released")compare({6'b0,64'd38,1'b0,expected_payload});
      check(!$isunknown(donor),"complete-known-source-owner");
      fd=$fopen(image,"w");check(fd!=0,"image-open");$fdisplay(fd,"%h",donor);$fclose(fd);
      $display("REGIONAL_STAGING_DONOR_PASS cut=%s bits=%0d target_cut=%0d",cut,OWNER_BITS,cycle);
    end else begin
      fd=$fopen(image,"r");check(fd!=0,"image-open");check($fscanf(fd,"%h",donor)==1,"image-read");$fclose(fd);
      load(donor);
      if(scenario=="bits")begin
        for(i=0;i<OWNER_BITS;i++)begin row=0;row[i]=1;load(row);row='1;row[i]=0;load(row);end
        load(donor);
      end else if(scenario=="label-drift")begin
        row=donor;row[BITS+1]=!row[BITS+1];load(row);
        @(negedge clock);#1;restore_hold=0;#1;
        check(snapshot_failed&&!snapshot_valid&&!capture_request_ready&&!capture_response_valid&&
          capture_clock_mask&&requests==0&&responses==0,"restored-label-drift-revokes-first-visibility");
        @(posedge clock);#1;check(snapshot_error[4],"restored-label-drift-sticky-error");
        $display("REGIONAL_STAGING_NEGATIVE_PASS case=%s loads=%0d requests=%0d responses=%0d",scenario,loads,requests,responses);$finish;
      end else if(scenario!="healthy")begin
        if(scenario=="busy")begin
          @(negedge clock);#1;restore_hold=0;capture_request_valid=1;#1;
          check(capture_request_ready,"start-public-bank-request");
          @(posedge clock);#1;capture_request_valid=0;#1;
        end
        @(negedge clock);#1;previous=control_state;restore_hold=1;restore_load=1;restore_state=~donor;
        if(scenario=="missing-owner")owner_present=0;
        else if(scenario=="physical-fault")cut_cycle_xor=1;
        else if(scenario=="request")snapshot_request=1;
        else if(scenario=="release")snapshot_release=1;
        else if(scenario=="borrow")capture_request_valid=1;
        else if(scenario=="unheld")restore_hold=0;
        else if(scenario=="reset")capture_reset=1;
        else check(scenario=="busy","known-negative");
        #1;check(!restore_ready&&!capture_request_ready&&!capture_response_valid&&capture_clock_mask,
          "unsafe-load-blocked-before-edge");
        @(posedge clock);#1;restore_load=0;#1;
        if(scenario=="reset")check(control_state==0,"reset-dominates-entire-load");
        else begin
          check(control_state[BITS+64:0]===previous[BITS+64:0],"unsafe-load-preserves-complete-payload-label-occupancy");
          check(snapshot_error!=0,"unsafe-load-sticky-error");
        end
        $display("REGIONAL_STAGING_NEGATIVE_PASS case=%s loads=%0d requests=%0d responses=%0d",scenario,loads,requests,responses);$finish;
      end
      compare(donor);
      if(cut=="occupied")begin
        @(negedge clock);#1;restore_hold=0;#1;
        check(snapshot_valid&&!snapshot_failed,"restored-occupied-owner-visible");
        padded=donor[BITS-1:0];
        for(i=0;i<WORDS;i++)begin
          snapshot_word_address=i;#1;check(!snapshot_word_error&&snapshot_word_data===padded[i*64+:64],"restored-word-padding");
          @(posedge clock);#1;compare(donor);
        end
        snapshot_word_address=WORDS;#1;check(snapshot_word_error&&snapshot_word_data==0,"restored-word-bound");
        repeat(128)begin @(posedge clock);#1;compare(donor);check(snapshot_valid&&!failed&&cycle==38,"sustained-cut-readback");end
      end
      $display("REGIONAL_STAGING_RESTORE_PASS cut=%s case=%s bits=%0d loads=%0d requests=%0d responses=%0d",cut,scenario,OWNER_BITS,loads,requests,responses);
    end
    $finish;
  end
  initial begin #200000;check(0,"timeout");end
endmodule
