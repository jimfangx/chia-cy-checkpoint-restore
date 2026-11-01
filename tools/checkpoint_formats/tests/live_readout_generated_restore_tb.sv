`timescale 1ns/1ps
module live_readout_generated_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0;always #5 clock=~clock;
  reg functional_reset=1,restore_hold=1,restore_load=0;
  reg functional_freeze=0;
  wire reset=1'b0;
  reg [68:0] restore_state=0;
  wire restore_ready;
  wire [68:0] control_state;
  wire [63:0] value;
  wire req_ready,resp_valid;
  wire permission=dut.checkpoint_live_readout_adapter.permission;
  wire request_ready=req_ready,response_valid=resp_valid;
  wire request_valid=1'b0,response_ready=1'b0;
  wire original_request_valid=dut.checkpoint_live_readout_adapter.original_request_valid;
  wire original_response_ready=dut.checkpoint_live_readout_adapter.original_response_ready;
  integer checks=0,loads=0;
  // The actual generated native/live shell keeps its original reset and
  // staging reset independent of the readout reset. Never reset the readout
  // owner: all 69 destination bits must enter through the generated ports.
  LiveTop dut(.clock(clock),.reset(functional_reset),.writeEn(1'b0),.address(2'b0),.data(64'b0),
    .value(value),.live(),.memoryOut(),
    .checkpoint_shell_ckpt_freeze(functional_freeze),.checkpoint_shell_ckpt_bank(8'b0),
    .checkpoint_shell_ckpt_slot(16'b0),.checkpoint_shell_ckpt_address(32'b0),
    .checkpoint_shell_ckpt_reset(1'b0),.checkpoint_shell_ckpt_req_valid(1'b0),
    .checkpoint_shell_ckpt_resp_ready(1'b0),.checkpoint_shell_ckpt_req_ready(req_ready),
    .checkpoint_shell_ckpt_resp_valid(resp_valid),
    .checkpoint_shell_live_snapshot_reset(1'b1),.checkpoint_shell_live_snapshot_request(1'b0),
    .checkpoint_shell_live_snapshot_release(1'b0),.checkpoint_shell_live_snapshot_owners_present(1'b1),
    .checkpoint_shell_live_snapshot_owners_frozen(1'b1),.checkpoint_shell_live_snapshot_target_cycle(64'b0),
    .checkpoint_shell_live_snapshot_word_address(32'b0),
    .checkpoint_live_readout_restore_hold(restore_hold),.checkpoint_live_readout_restore_load(restore_load),
    .checkpoint_live_readout_restore_state(restore_state),.checkpoint_live_readout_restore_ready(restore_ready),
    .checkpoint_live_readout_control_state(control_state));
  task check(input bit ok,input string why);
    checks++;
    if(!ok)begin
      $display("GENERATED_READOUT_RESTORE_DIVERGENCE signal=%s loads=%0d checks=%0d",why,loads,checks);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task load(input [68:0] state_in);
    @(negedge clock);restore_state=state_in;restore_load=1;#1;
    check(restore_ready&&!req_ready&&!resp_valid,"generated-load-qualified");
    @(posedge clock);#1;loads++;restore_load=0;
    check(control_state===state_in,"generated-complete-control-before-ack");
    check(dut.checkpoint_live_readout_adapter.pending===state_in[0]&&
      dut.checkpoint_live_readout_adapter.snapshot_owner===state_in[1]&&
      dut.checkpoint_live_readout_adapter.snapshot_bank.saved_data===state_in[65:2]&&
      dut.checkpoint_live_readout_adapter.snapshot_bank.saved_error===state_in[66]&&
      dut.checkpoint_live_readout_adapter.snapshot_bank.pending===state_in[67]&&
      dut.checkpoint_live_readout_adapter.snapshot_bank.failed===state_in[68],"generated-independent-original-registers");
    repeat(2)begin @(posedge clock);#1;
      check(control_state===state_in&&!req_ready&&!resp_valid,"generated-parked-owner");end
  endtask
  reg [68:0] row;
  initial begin
    $dumpfile("generated-readout-restore.vcd");$dumpvars(0,live_readout_generated_restore_tb);
    // Original register reset is inside its original functional hold guard.
    // Initialize that separate owner before freezing it; the readout reset
    // stays deasserted throughout this fresh local-owner restore process.
    repeat(2)begin @(posedge clock);#1;end
    @(negedge clock);functional_freeze=1;
    load(69'h123456789abcdef00);
    @(negedge clock);functional_reset=0;
    for(integer b=0;b<69;b++)begin
      row=0;row[b]=1;if(b==67)begin row[0]=1;row[1]=1;end
      load(row);
      row='1;row[b]=0;if(b==0||b==1)row[67]=0;if(b==67)row[0]=0;
      load(row);
    end
    check(value===0,"original-functional-freeze-still-bound");
    $display("GENERATED_READOUT_RESTORE_PASS loads=%0d checks=%0d owner_bits=69 ack=0",loads,checks);$finish;
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
