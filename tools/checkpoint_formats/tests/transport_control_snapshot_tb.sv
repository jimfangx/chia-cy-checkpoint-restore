`timescale 1ns/1ps
`ifndef SNAPSHOT_GATES
`define SNAPSHOT_GATES 3
`endif
module transport_control_snapshot_tb;
  import "DPI-C" function void checkpoint_network_fail();
  localparam GATES=`SNAPSHOT_GATES, BITS=481+GATES, WORDS=(BITS+63)/64;
  reg clock=0, reset=1;
  always #5 clock=!clock;
  reg [BITS-1:0] live_state=0;
  reg [63:0] target_cycle=0;
  reg cut_valid=0, owner_error=0, request_valid=0, release_snapshot=0, abort_snapshot=0;
  wire request_ready, snapshot_valid, word_valid;
  wire [63:0] snapshot_cycle, word_data;
  wire [2:0] error;
  reg [31:0] word_index=0;
  CheckpointTransportControlSnapshot #(.GATES(GATES)) dut(.*);
  integer checks=0, captures=0, word_checks=0, bit_index, epoch;
  reg [BITS-1:0] expected;
  reg [63:0] expected_cycle;
  task check(input bit ok, input string signal_name);
    checks++;
    if(!ok) begin
      $display("SNAPSHOT_DIVERGENCE cycle=%0d signal=%s word=%0d captures=%0d",target_cycle,signal_name,word_index,captures);
      // The DPI failure helper exits immediately to preserve nonzero status.
      // SP2 schedules the flush at the end of the time slot. Allow one
      // picosecond for it, without reaching another raw or target clock edge.
      $dumpflush; #0.001;
      checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task tick; @(posedge clock); #1; endtask
  task edge_start; @(negedge clock); #1; endtask
  task reset_owner;
    edge_start; reset=1; request_valid=0; release_snapshot=0; abort_snapshot=0;
    cut_valid=0; owner_error=0;
    #1; check(!request_ready && !snapshot_valid && !word_valid && word_data==0,"reset combinational invalidation");
    tick; check(error==0 && snapshot_cycle==0,"reset clears owner and label");
    edge_start; reset=0; #1; check(request_ready,"reset recovery");
  endtask
  task read_all;
    check(snapshot_valid && snapshot_cycle===expected_cycle,"snapshot label");
    for(integer w=WORDS-1;w>=0;w--) begin
      word_index=w; #0.01;
      check(word_valid && word_data===(expected >> (64*w) & 64'hffffffffffffffff),"snapshot word");
      word_checks++;
    end
    word_index=WORDS; #0.01; check(!word_valid && word_data==0,"past-end address");
    word_index=32'hffffffff; #0.01; check(!word_valid && word_data==0,"maximum invalid address");
    // In particular, a multiply-overflow address must not alias word zero.
    word_index=32'h04000000; #0.01; check(!word_valid && word_data==0,"overflow invalid address");
  endtask
  task capture;
    edge_start; cut_valid=1; owner_error=0; request_valid=1;
    expected=live_state; expected_cycle=target_cycle;
    #1; check(request_ready && !snapshot_valid,"capture admission");
    tick; captures++; check(!request_ready && snapshot_valid && error==0,"atomic publication");
    edge_start; request_valid=0; cut_valid=0;
    // All source bits and the target label advance after the copied edge.
    // Multiword reads must continue to return ONLY the saved epoch.
    live_state=~expected; target_cycle=target_cycle+7; owner_error=1;
    repeat(3) begin tick; read_all; end
    // A busy producer cannot overwrite the valid epoch, even if it asserts a
    // request at another acknowledged cut. It must observe backpressure.
    edge_start; request_valid=1; cut_valid=1; owner_error=0;
    repeat(3) begin tick; check(!request_ready,"busy backpressure"); read_all; end
    edge_start; release_snapshot=1;
    #1; check(!snapshot_valid && !word_valid && !request_ready,"release invalidation and epoch separation");
    tick; check(error==0,"valid release");
    edge_start; request_valid=0; release_snapshot=0; cut_valid=0;
  endtask
  initial begin
    $dumpfile("transport-control-snapshot.vcd"); $dumpvars(0,transport_control_snapshot_tb);
    reset_owner;
    // Exhaustively distinguish every packed bit, including chunk boundaries
    // and the last padded word, independent of the RTL's internal registers.
    for(bit_index=0;bit_index<BITS;bit_index++) begin
      live_state=0; live_state[bit_index]=1; target_cycle=bit_index+100;
      capture;
    end
    for(epoch=0;epoch<32;epoch++) begin
      for(bit_index=0;bit_index<BITS;bit_index++) live_state[bit_index]=$random;
      target_cycle=64'hffffffff00000000+epoch;
      capture;
    end
    // No cut / explicit owner fault / both must fail before any valid word.
    for(epoch=1;epoch<4;epoch++) begin
      reset_owner;
      edge_start; cut_valid=!(epoch&1); owner_error=(epoch&2)!=0; request_valid=1;
      tick; check(error==epoch && !snapshot_valid && !word_valid && word_data==0,"invalid admission");
      edge_start; request_valid=0; abort_snapshot=1;
      tick; check(error==epoch && !request_ready,"abort retains sticky fault");
    end
    reset_owner;
    edge_start; release_snapshot=1;
    tick; check(error==4 && !snapshot_valid,"release without epoch");
    reset_owner;
    edge_start; request_valid=1; cut_valid=1; abort_snapshot=1;
    tick; check(error==0 && !snapshot_valid,"abort wins over accepting edge");
    reset_owner;
    edge_start; request_valid=1; cut_valid=1;
    tick; check(snapshot_valid,"epoch before abort");
    edge_start; request_valid=0; abort_snapshot=1;
    #1; check(!snapshot_valid && !word_valid && word_data==0,"abort immediate invalidation");
    tick;
    edge_start; abort_snapshot=0;
    #1; check(request_ready && !snapshot_valid && error==0,"abort recovery");
    live_state='1; target_cycle=777; capture;
    edge_start; request_valid=1; cut_valid=1;
    tick; check(snapshot_valid,"epoch before reset");
    reset_owner;
    live_state='1; target_cycle=888; capture;
    $display("SNAPSHOT_PASS gates=%0d bits=%0d captures=%0d checks=%0d word_checks=%0d",GATES,BITS,captures,checks,word_checks);
    $finish;
  end
  initial begin #1000000; check(0,"timeout"); end
endmodule
