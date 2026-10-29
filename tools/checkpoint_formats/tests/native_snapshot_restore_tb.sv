`timescale 1ns/1ps
`ifndef SNAPSHOT_BITS
`define SNAPSHOT_BITS 130
`endif
module native_snapshot_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=`SNAPSHOT_BITS, WORDS=(BITS+63)/64;
  reg clock=0; always #5 clock=~clock;
  reg reset=0,request=0,release_snapshot=0,restore_hold=1,restore_load=0;
  reg owners_present=1,functional_frozen=1,reader_idle=1,borrow_attempt=0;
  reg [63:0] target_cycle=0;
  reg [BITS-1:0] live_state=0;
  reg [31:0] word_address=0;
  reg [BITS+70:0] restore_state=0;
  wire request_ready,valid,borrow_enable,failed,word_error,restore_ready;
  wire [63:0] word_data,cut_cycle;
  wire [5:0] error;
  wire [BITS-1:0] snapshot_state;
  wire [BITS+70:0] control_state;
  CheckpointNativeStateSnapshot #(.BITS(BITS),.RESTORE_ENABLE(1)) dut(.*);
  reg [BITS+70:0] image[0:0];
  reg [BITS-1:0] expected;
  reg [WORDS*64-1:0] padded;
  reg [BITS+64:0] previous_payload_and_label;
  reg [5:0] expected_error;
  integer checks=0,reads=0,target_edges=0,fd;
  string mode,cut,scenario,image_path;
  task check(input bit ok,input string why);
    checks++;
    if(!ok)begin
      $display("RESTORE_DIVERGENCE signal=%s bits=%0d cut=%s case=%s target_edges=%0d ack=0 reads=%0d",why,BITS,cut,scenario,target_edges,reads);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task neg; @(negedge clock);#1;endtask
  task edge_done; @(posedge clock);#1;endtask
  task capture;
    neg();request=1;expected=live_state;
    #1;check(request_ready && !borrow_enable,"capture-before-borrow");
    edge_done();request=0;
    #1;check(snapshot_state===expected && valid && cut_cycle===target_cycle,"continuation-new-capture");
  endtask
  task words;
    padded=0;padded[BITS-1:0]=expected;
    for(integer w=0;w<WORDS;w++)begin
      neg();word_address=w;live_state=~live_state;
      #1;check(!word_error && word_data===padded[w*64+:64],"independent-word-and-padding");reads++;
      edge_done();check(snapshot_state===expected,"retained-under-live-vector-change");
    end
    neg();word_address=32'hffffffff;
    #1;check(word_error && word_data==0 && valid,"unsigned-address-no-alias");
  endtask
  initial begin
    $dumpfile("native-snapshot-restore.vcd");$dumpvars(0,native_snapshot_restore_tb);
    check($value$plusargs("MODE=%s",mode),"mode-required");
    check($value$plusargs("CUT=%s",cut),"cut-required");
    check($value$plusargs("IMAGE=%s",image_path),"image-required");
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    for(integer b=0;b<BITS;b++)live_state[b]=((b*13+7)%19)<9;
    if(mode=="donor")begin
      restore_hold=0;reset=1;repeat(2)edge_done();neg();reset=0;
      target_cycle=64'hfedcba9876543210;
      if(cut!="empty")capture();
      if(cut=="released" || cut=="preborrow")begin
        neg();release_snapshot=1;edge_done();release_snapshot=0;
      end
      if(cut=="error")begin
        neg();target_cycle++;owners_present=0;functional_frozen=0;reader_idle=0;
        request=1;release_snapshot=1;edge_done();request=0;release_snapshot=0;
        check(error===6'd55,"donor-five-sticky-faults");
      end
      if(cut=="preborrow")begin
        neg();borrow_attempt=1;edge_done();borrow_attempt=0;
        check(error===6'd8,"donor-premature-borrow-fault");
      end
      fd=$fopen(image_path,"w");check(fd!=0,"donor-file-open");
      $fdisplay(fd,"%h",control_state);$fclose(fd);
      $display("RESTORE_DONOR_PASS bits=%0d cut=%s checks=%0d",BITS,cut,checks);$finish;
    end
    check(mode=="restore","known-mode");
    // A fresh process with no destination reset and no hierarchical writes.
    // The complete owner enters only through its synthesized restore interface.
    $readmemh(image_path,image);restore_state=image[0];
    target_cycle=restore_state[BITS+64:BITS+1];
    neg();restore_load=1;
    #1;check(restore_ready && !valid && !borrow_enable && !request_ready && word_error,"parked-load-qualification");
    edge_done();restore_load=0;
    check(control_state===image[0],"complete-control-before-target");
    check(snapshot_state===image[0][BITS-1:0] && cut_cycle===image[0][BITS+64:BITS+1] &&
          error===image[0][BITS+70:BITS+65],"independent-field-readback");
    repeat(8)begin
      neg();live_state=~live_state;target_cycle++;
      edge_done();check(control_state===image[0] && !valid && !borrow_enable && word_error,"parked-owner-immutable");
    end
    neg();target_cycle=cut_cycle;
    if(scenario=="bit-coverage")begin
      // Every original staging/control bit is loaded as both a walking one
      // and a walking zero, while parked; no serialized word is acknowledged.
      for(integer b=0;b<BITS+71;b++)begin
        for(integer polarity=0;polarity<2;polarity++)begin
          neg();restore_state=0;restore_state[b]=1;
          if(polarity)restore_state=~restore_state;
          restore_load=1;
          #1;check(restore_ready && !valid && !borrow_enable,"per-bit-load-qualified");
          edge_done();restore_load=0;
          check(control_state===restore_state,"per-bit-complete-readback");
          check(snapshot_state===restore_state[BITS-1:0] && cut_cycle===restore_state[BITS+64:BITS+1] &&
                error===restore_state[BITS+70:BITS+65],"per-bit-independent-fields");
        end
      end
      neg();reset=1;restore_load=1;restore_state='1;
      #1;check(!restore_ready && !valid && !borrow_enable && word_error,"reset-over-load-before-ack");
      edge_done();check(control_state===0,"reset-over-load-complete-owner");
      $display("RESTORE_BIT_COVERAGE_PASS bits=%0d owner_bits=%0d loads=%0d checks=%0d ack=0",BITS,BITS+71,2*(BITS+71),checks);$finish;
    end
    if(scenario!="healthy")begin
      check(cut=="occupied","negative-occupied-donor-required");
      previous_payload_and_label=control_state[BITS+64:0];
      // A different incoming payload must never partially overwrite old state.
      restore_state=~image[0];restore_load=1;
      case(scenario)
        "held-request":begin request=1;expected_error=32;end
        "held-release":begin release_snapshot=1;expected_error=32;end
        "held-borrow":begin borrow_attempt=1;expected_error=8;end
        "held-busy":begin reader_idle=0;expected_error=4;end
        "held-owner":begin owners_present=0;expected_error=1;end
        "held-freeze":begin functional_frozen=0;expected_error=2;end
        "unheld-load":begin restore_hold=0;expected_error=32;end
        "unpark-drift":begin restore_load=0;restore_hold=0;target_cycle++;expected_error=16;end
        "unpark-owner":begin restore_load=0;restore_hold=0;owners_present=0;expected_error=1;end
        "unpark-freeze":begin restore_load=0;restore_hold=0;functional_frozen=0;expected_error=2;end
        "held-overlap":begin request=1;release_snapshot=1;expected_error=32;end
        "held-borrow-busy":begin borrow_attempt=1;reader_idle=0;expected_error=12;end
        default:check(0,"known-negative");
      endcase
      #1;check(failed && !valid && !borrow_enable && !request_ready && !restore_ready && word_error && word_data==0,"unsafe-restore-revoked-before-ack");
      edge_done();check(control_state[BITS+64:0]===previous_payload_and_label && error===expected_error,"unsafe-load-no-partial-state");
      neg();restore_hold=1;restore_load=0;request=0;release_snapshot=0;borrow_attempt=0;
      owners_present=1;functional_frozen=1;reader_idle=1;target_cycle=cut_cycle;
      repeat(4)begin edge_done();check(error===expected_error && failed && !valid,"restore-error-sticky");end
      neg();restore_state=image[0];restore_load=1;
      #1;check(restore_ready && !valid,"explicit-whole-owner-recovery-qualified");
      edge_done();restore_load=0;
      check(control_state===image[0],"recovery-restores-entire-owner");
      $display("RESTORE_NEGATIVE_PASS bits=%0d case=%s error=%0d checks=%0d target_edges=0 ack=0",BITS,scenario,expected_error,checks);$finish;
    end
    // Release only after independent complete readback. This is a component
    // raw-clock continuation, not a target/environment ownership handshake.
    restore_hold=0;
    #1;
    if(error!=0)begin
      check(failed && !valid && !borrow_enable,"donor-errors-remain-sticky-on-unpark");
      repeat(4)begin edge_done();check(control_state===image[0],"donor-fault-state-exact");end
      neg();reset=1;edge_done();neg();reset=0;
    end else if(image[0][BITS])begin
      expected=image[0][BITS-1:0];
      check(valid && !failed,"restored-occupied-owner-usable");words();
      neg();release_snapshot=1;
      #1;check(!borrow_enable && !valid,"continued-release-before-ack");
      edge_done();release_snapshot=0;
    end else check(request_ready && !failed && !valid,"restored-empty-owner-usable");
    neg();target_cycle+=91;live_state=~image[0][BITS-1:0];capture();words();
    repeat(128)begin edge_done();check(valid && snapshot_state===expected,"continued-component-execution");end
    $display("RESTORE_PASS bits=%0d cut=%s checks=%0d reads=%0d raw_continuation=128 target_edges=0",BITS,cut,checks,reads);$finish;
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
