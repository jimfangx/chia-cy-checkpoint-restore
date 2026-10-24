`timescale 1ns/1ps
// Generated network plus real cut controller and independent arithmetic oracle. No hierarchical
// state observation in this test is a production hardware capture path.
module physical_clock_wiring_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, reset=1, request=0, reference_clock=0;
  wire mask, stopped, read_enable, failed;
  wire [2:0] error;
  wire [63:0] cut_cycle;
  wire [1:0] captured_ce;
  wire [7:0] a,b;
  wire [63:0] count;
  wire [1:0] ce;
  reg [7:0] expected_a=0, expected_b=0;
  reg [63:0] expected_count=0;
  wire [1:0] expected_ce=reset ? 2'b11 : {expected_count[1],expected_count[0]};
  wire [1:0] reference_gate;
  PhysicalClockWiringFixture dut(.clock(clock),.reset(reset),.freeze_request(request),
    .a(a),.b(b),.count(count),.ce(ce),.clock_mask(mask),.stopped(stopped),
    .read_enable(read_enable),.failed(failed),.captured_ce(captured_ce),.cut_cycle(cut_cycle),.error(error));
  BUFGCE reference_left(.I(reference_clock),.CE(expected_ce[0]),.O(reference_gate[0]));
  BUFGCE reference_right(.I(reference_clock),.CE(expected_ce[1]),.O(reference_gate[1]));
  integer checks=0, cycles=0, cuts=0, stalls=0, root_edges=0, left_edges=0, right_edges=0;
  integer saved_root, saved_left, saved_right;
  bit corrupt;
  always @(posedge dut.network.checkpoint_physical_root_gate_O) root_edges++;
  always @(posedge dut.network.left.gate_O) left_edges++;
  always @(posedge dut.network.right.gate_O) right_edges++;
  task check(input bit ok,input string why);
    checks++;
    if(!ok) begin
      $display("CLOCK_WIRING_DIVERGENCE cycle=%0d signal=%s acknowledged_edges=0",cycles,why);
      $dumpflush;
      checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task compare;
    check(a===expected_a,"left.saved"); check(b===expected_b,"right.saved");
    check(count===expected_count,"cycles"); check(ce===expected_ce,"logical_ce");
  endtask
  task step;
    clock=0; reference_clock=0; #3;
    if(reset) begin expected_a=0; expected_b=0; expected_count=0; end
    else begin
      if(expected_ce[0]) expected_a=expected_a+3;
      if(expected_ce[1]) expected_b=expected_b+3;
      expected_count=expected_count+1;
    end
    clock=1; reference_clock=1; #3;
    if(!reset) begin cycles++; compare(); end
  endtask
  task capture;
    request=1;
    clock=0; reference_clock=0; #3;
    check(mask===1,"falling_edge_mask");
    check(dut.network.left.gate.enable_clk===0 && dut.network.right.gate.enable_clk===0 &&
          dut.network.checkpoint_physical_root_gate.enable_clk===0,"physical_latches_masked");
    check(ce[0]===reference_left.enable_clk && ce[1]===reference_right.enable_clk,"logical_latch_mapping");
    if(corrupt && cycles==17) check(ce===(expected_ce^1),"logical_ce[0]");
    saved_root=root_edges; saved_left=left_edges; saved_right=right_edges;
    cuts++;
    $display("CLOCK_WIRING_CUT cycle=%0d count=%0d logical_ce=%b",cycles,count,ce);
    repeat(16) begin
      clock=1; #3; compare();
      check(read_enable && stopped && !failed && error==0,"atomic_cut_permission");
      check(captured_ce===expected_ce && cut_cycle==expected_count,"atomic_cut_label_and_ce");
      check(root_edges==saved_root && left_edges==saved_left && right_edges==saved_right,"no_functional_edge");
      check(dut.network.checkpoint_physical_root_gate_O===0 && dut.network.left.gate_O===0 && dut.network.right.gate_O===0,"all_outputs_low");
      clock=0; #3; stalls++;
    end
    // Release only on the next common falling edge. The reference remains
    // stopped until that same functional edge, with original native CE state.
    clock=1; #3; request=0;
    clock=0; #3; clock=1; #3;
    check(mask && !read_enable,"registered_release_validation");
    step();
    check(!mask,"release");
  endtask
  initial begin
    corrupt=$test$plusargs("corrupt");
    $dumpfile("physical-clock-wiring.vcd"); $dumpvars(0,physical_clock_wiring_tb);
    // Preserve the unmodified vendor global startup/reset interval.
    #120;
    repeat(4) step(); reset=0;
    while(cycles<320) begin
      if(cycles==0 || cycles==17 || cycles==128 || cycles==256) capture(); else step();
    end
    check(cuts==4 && stalls==64,"complete_cut_scope");
    $display("CLOCK_WIRING_PASS checks=%0d cycles=%0d cuts=%0d stalls=%0d",checks,cycles,cuts,stalls);
    $finish;
  end
  initial begin #100000; check(0,"timeout"); end
endmodule
