`timescale 1ns/1ps
`ifndef PHYSICAL_RESTORE_GATES
`define PHYSICAL_RESTORE_GATES 0
`endif
module physical_transport_restore_specialization_tb;
  import "DPI-C" function void checkpoint_network_fail();
  localparam GATES=`PHYSICAL_RESTORE_GATES;
  reg clock=0, reset=1, apply_valid=0;
  always #5 clock=!clock;
  wire apply_ready, applied, restore_hold, restore_load_pos, restore_load_neg, busy;
  wire [GATES+480:0] restore_state;
  wire [4:0] error;
  CheckpointTransportPhysicalRestore #(.GATES(GATES)) dut(
    .clock(clock),.reset(reset),.apply_valid(apply_valid),.apply_state({(481+GATES){1'b0}}),
    .apply_cycle(64'd1),.expected_cycle(64'd1),.cut_valid(1'b1),
    .owners_quiescent(1'b1),.owner_error(1'b0),.observed_state({(481+GATES){1'b0}}),.*);
  initial begin
    $dumpfile("physical-restore-specialization.vcd"); $dumpvars(0,physical_transport_restore_specialization_tb);
    repeat(3) @(negedge clock);
    #1; reset=0; apply_valid=1;
    repeat(4) begin
      @(posedge clock); #1;
      if(!error[4] || apply_ready || applied || restore_load_pos || restore_load_neg || !restore_hold) begin
        $display("PHYSICAL_RESTORE_SPECIALIZATION_DIVERGENCE gates=%0d",GATES);
        $dumpflush; #0.001; checkpoint_network_fail(); $fatal(1,"failure helper returned");
      end
    end
    $display("PHYSICAL_RESTORE_SPECIALIZATION_REJECT gates=%0d acks=0 writes=0",GATES);
    $finish;
  end
endmodule
