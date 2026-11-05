`timescale 1ns/1ps
// This migrates only the generated two-edge cut controller and its pending
// owner. DUT/endpoints are deliberately outside this parked component test.
module regional_controller_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=75;
  reg clock=0; always #5 clock=!clock;
  reg reset=1, capture_reset=1, freeze_request=0, owner_present=1, write=0;
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
  reg [15:0] capture_slot=`CYCLE_SLOT;
  reg [31:0] capture_address=0;
  wire [63:0] capture_response_data;
  reg restore_hold=0, restore_load_pos=0, restore_load_neg=0;
  reg [BITS-1:0] restore_state=0;
  wire [BITS-1:0] control_state;
  reg [63:0] restored_cycle=0;
  bit destination;
  wire [63:0] controller_target_cycle=destination ? restored_cycle : cycle;
  NativeRegionsFixture dut(.*);
  string mode, image;
  integer fd, count=0, checks=0, corrupt_bit=-1, acknowledgements=0, functional_edges=0;
  reg [BITS-1:0] donor, prior;
  reg [63:0] label;
  task check(input bit ok, input string why);
    checks++;
    if(!ok) begin
      $display("REGIONAL_CONTROLLER_FAILURE reason=%s record=%0d",why,count);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  always @(posedge clock) begin
    if(capture_request_ready && capture_request_valid) acknowledgements++;
    if(capture_response_valid && capture_response_ready) acknowledgements++;
  end
  // Both selected original root clocks must stay parked in a destination.
  always @(posedge dut.host.stage.network.checkpoint_physical_root_gate_O)
    if(destination) functional_edges++;
  always @(posedge dut.host.stage.peer.checkpoint_physical_root_gate_O)
    if(destination) functional_edges++;
  task tick; @(posedge clock); #2; endtask
  task low; @(negedge clock); #1; endtask
  task blocked;
    check(capture_clock_mask && !capture_read_enable && !capture_request_ready &&
      !capture_response_valid && capture_response_data===0 && !capture_response_error,
      "held mask, permission and all external transport signals");
    check(acknowledgements==0 && functional_edges==0,"no destination transport or functional edge");
  endtask
  task record;
    check((^control_state)!==1'bx,"complete actual donor state known");
    $fdisplay(fd,"%h %h",control_state,cycle);
    count++;
  endtask
  initial begin
    $dumpfile("regional-controller-restore.vcd"); $dumpvars(0,regional_controller_restore_tb);
    check($value$plusargs("mode=%s",mode) && $value$plusargs("image=%s",image),"explicit invocation");
    destination=mode=="destination";
    if($value$plusargs("corrupt_bit=%d",corrupt_bit)) check(destination,"destination corruption only");
    fd=$fopen(image,destination?"r":"w"); check(fd!=0,"actual component donor file");
    if(destination) begin
      // Assert before the first raw edge. Neither reset nor DUT preparation is
      // used as a substitute for loading any of the controller's original bits.
      restore_hold=1; capture_reset=0; reset=0;
      #120;
      while($fscanf(fd,"%h %h",donor,label)==2) begin
        low(); restored_cycle=label;
        restore_state=donor ^ (corrupt_bit>=0 && count==0 ? (BITS'(1)<<corrupt_bit) : BITS'(0));
        restore_load_neg=1;
        // The falling-edge mask and positive-edge fields are separate owners.
        low(); restore_load_neg=0; restore_load_pos=1;
        tick(); restore_load_pos=0; #1;
        if(control_state!==donor) begin
          $display("REGIONAL_CONTROLLER_FIRST_DIVERGENCE signal=control_state record=%0d target_cycle=%0d expected=%h observed=%h acknowledged_edges=%0d functional_edges=%0d",count,label,donor,control_state,acknowledgements,functional_edges);
          checkpoint_widget_failed(); $finish;
        end
        blocked();
        // Real unsolicited traffic, owner withdrawal and changing selectors
        // cannot mutate any original controller or pending field under hold.
        capture_request_valid=1; capture_response_ready=1; freeze_request=0; owner_present=0;
        repeat(8) begin tick(); blocked(); check(control_state===donor,"independent complete held readback"); end
        low(); capture_request_valid=0; capture_response_ready=0;
        // Reject unheld load strobes, while retaining the mask for safety.
        restore_hold=0; restore_load_pos=1; restore_load_neg=1; restore_state=~donor;
        tick(); low(); blocked(); check(control_state===donor,"unheld complete load rejected");
        restore_hold=1; restore_load_pos=0; restore_load_neg=0;
        count++;
      end
      check(count==11,"all independent donor records consumed");
      capture_reset=1; restore_load_pos=1; restore_load_neg=1; restore_state='1;
      low(); tick(); blocked(); check(control_state===0,"shared reset dominates both load domains");
    end else begin
      #120; tick(); tick(); low(); capture_reset=0; reset=0;
      repeat(17) tick(); record();
      freeze_request=1; low(); record();
      tick(); check(capture_read_enable,"common low-phase cut sampled"); record();
      low(); capture_request_valid=1; tick(); capture_request_valid=0;
      check(control_state[74],"actual generated pending request owner"); record();
      repeat(8) tick(); check(capture_response_valid,"actual endpoint stalled response"); record();
      low(); capture_response_ready=1; tick(); capture_response_ready=0; record();
      low(); freeze_request=0; tick(); record();
      low(); record(); tick(); record();
      low(); owner_present=0; freeze_request=1; low(); tick();
      check(failed && error[0],"actual missing-owner sticky fault"); record();
      low(); capture_reset=1; low(); tick(); record();
      check(count==11,"complete donor phases");
    end
    $fclose(fd);
    $display("REGIONAL_CONTROLLER_RESTORE_PASS mode=%s records=%0d checks=%0d acknowledgements=%0d functional_edges=%0d",mode,count,checks,acknowledgements,functional_edges);
    $finish;
  end
endmodule
