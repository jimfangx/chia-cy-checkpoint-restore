`timescale 1ns/1ps
`ifndef SNAPSHOT_BITS
`define SNAPSHOT_BITS 130
`endif
module native_state_snapshot_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=`SNAPSHOT_BITS, WORDS=(BITS+63)/64;
  reg clock=0; always #5 clock=~clock;
  reg reset=1,request=0,release_snapshot=0;
  // This retained capture-only suite intentionally leaves destination loading
  // disabled. A separate fresh-process suite verifies the opt-in restore ABI.
  wire restore_hold=1'b0,restore_load=1'b0,restore_ready;
  wire [BITS+70:0] restore_state=0;
  reg owners_present=1,functional_frozen=1,reader_idle=1,borrow_attempt=0;
  reg [63:0] target_cycle=37;
  reg [BITS-1:0] live_state=0;
  reg [31:0] word_address=0;
  wire request_ready,valid,borrow_enable,failed,word_error;
  wire [63:0] word_data,cut_cycle;
  wire [5:0] error;
  wire [BITS-1:0] snapshot_state;
  wire [BITS+70:0] control_state;
  CheckpointNativeStateSnapshot #(.BITS(BITS)) dut(.*);
  reg [BITS-1:0] expected;
  reg [WORDS*64-1:0] padded;
  integer checks=0,reads=0,captures=0;
  string scenario;
  task check(input bit ok,input string why);
    checks++;
    if(!ok)begin
      $display("NATIVE_SNAPSHOT_DIVERGENCE signal=%s scenario=%s cycle=%0d address=%0d ack=0 reads=%0d",why,scenario,target_cycle,word_address,reads);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task neg; @(negedge clock);#1;endtask
  task edge_done; @(posedge clock);#1;endtask
  task sample;
    neg();request=1;expected=live_state;
    #1;check(request_ready && !borrow_enable && word_error,"no borrowing before snapshot");
    edge_done();request=0;
    #1;check(valid && borrow_enable && !failed && cut_cycle==target_cycle,"atomic acceptance");
    check(snapshot_state===expected,"complete preedge vector");captures++;
  endtask
  task allwords;
    padded=0;padded[BITS-1:0]=expected;
    for(integer w=0;w<WORDS;w++)begin
      neg();word_address=w;
      #1;check(!word_error && word_data===padded[w*64+:64],"all staged words and zero padding");reads++;
      live_state=~live_state;
      edge_done();check(snapshot_state===expected,"stable under changing live state");
    end
    for(integer w=0;w<3;w++)begin
      neg();word_address=w==0?WORDS:(w==1?32'h04000000:32'hffffffff);
      #1;check(word_error && word_data===64'b0 && valid && !failed,"out of range cannot alias");
    end
  endtask
  initial begin
    $dumpfile("native-state-snapshot.vcd");$dumpvars(0,native_state_snapshot_tb);
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    repeat(2)edge_done();neg();reset=0;
    for(integer b=0;b<BITS;b++)live_state[b]=(b%7)<3;
    #1;check(!valid && !failed && request_ready && word_error && word_data==0,"empty state");
    if(scenario=="healthy")begin
      repeat(5)begin
        sample();
        neg();borrow_attempt=1;reader_idle=0;
        allwords();
        neg();borrow_attempt=0;reader_idle=1;release_snapshot=1;
        #1;check(!borrow_enable && !valid && word_error,"release revokes before edge");
        edge_done();release_snapshot=0;
        #1;check(!valid && !failed && snapshot_state===expected,"release retains prior payload");
        neg();target_cycle+=19;live_state=~live_state;
      end
      sample();neg();reset=1;
      #1;check(!valid && !borrow_enable && word_error,"reset revokes before edge");
      edge_done();check(snapshot_state==0 && cut_cycle==0 && error==0,"reset clears own state");
      $display("NATIVE_SNAPSHOT_PASS bits=%0d captures=%0d reads=%0d checks=%0d",BITS,captures,reads,checks);$finish;
    end else begin : negative
      reg [5:0] expected_error;
      bit pre_capture;
      pre_capture=scenario=="missing-owner" || scenario=="no-freeze" || scenario=="busy-capture" ||
        scenario=="borrow-before" || scenario=="sameedge-borrow" || scenario=="early-release" || scenario=="overlap";
      if(!pre_capture)sample();
      else expected=0;
      neg();
      case(scenario)
        "missing-owner":begin owners_present=0;request=1;expected_error=1;end
        "no-freeze":begin functional_frozen=0;request=1;expected_error=2;end
        "busy-capture":begin reader_idle=0;request=1;expected_error=4;end
        "borrow-before":begin borrow_attempt=1;expected_error=8;end
        "sameedge-borrow":begin request=1;borrow_attempt=1;expected_error=12;end
        "drift":begin target_cycle++;expected_error=16;end
        "lost-freeze":begin functional_frozen=0;expected_error=2;end
        "missing-after":begin owners_present=0;expected_error=1;end
        "duplicate":begin request=1;expected_error=32;end
        "busy-release":begin reader_idle=0;release_snapshot=1;expected_error=4;end
        "early-release":begin release_snapshot=1;expected_error=32;end
        "overlap":begin request=1;release_snapshot=1;expected_error=32;end
        default:check(0,"unknown scenario");
      endcase
      #1;check(failed && !valid && !borrow_enable && !request_ready && word_error && word_data==0,"fault revokes before acknowledgement");
      edge_done();
      check(error===expected_error && snapshot_state===expected,"fault sticky exact owner and payload");
      neg();owners_present=1;functional_frozen=1;reader_idle=1;borrow_attempt=0;request=0;release_snapshot=0;
      target_cycle=cut_cycle;
      repeat(3)begin edge_done();check(failed && !valid && !borrow_enable && word_error && snapshot_state===expected,"cannot clear fault by repairing inputs");end
      neg();reset=1;edge_done();neg();reset=0;
      #1;check(!failed && !valid && request_ready,"explicit reset recovery");
      sample();allwords();
      $display("NATIVE_SNAPSHOT_NEGATIVE_PASS case=%s error=%0d checks=%0d",scenario,expected_error,checks);$finish;
    end
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
