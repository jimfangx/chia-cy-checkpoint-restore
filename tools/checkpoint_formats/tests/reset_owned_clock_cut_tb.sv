`timescale 1ns/1ps
// Independent unmasked vendor gates and functional scoreboard. No state access
// through simulation backdoors is used by the cut or reset-owner hardware.
module reset_owned_clock_cut_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0, reference_clock=0, controller_reset=1, freeze_request=0;
  reg [1:0] reset_in=3, reference_reset=3;
  reg [3:0] owner_present=15;
  reg reset_writer_present=1;
  wire [1:0] functional_reset, captured_reset;
  wire root_clock, clock_mask, stopped, read_enable, failed;
  wire [2:0] gate_clock, reference_gate, captured_ce, physical_error, reset_error;
  wire [77:0] control_state;
  wire external_root, external_mask, external_read, external_failed;
  wire [2:0] external_gates;
  wire [1:0] external_reset;
  wire [77:0] external_state;
  wire [63:0] cut_cycle;
  reg [63:0] target_cycle=0, reference_cycle=0;
  reg [31:0] state[3], expected_state[3];
  // VCS VCD does not emit unpacked array words through $dumpvars. Explicit
  // packed views retain every original functional and reference bit.
  wire [95:0] functional_words={state[2],state[1],state[0]};
  wire [95:0] reference_words={expected_state[2],expected_state[1],expected_state[0]};
  wire [2:0] ce = functional_reset[0] ? 3'b111 :
      {target_cycle[1]^target_cycle[0], target_cycle[2], !target_cycle[0]};
  wire [2:0] reference_ce = reference_reset[0] ? 3'b111 :
      {reference_cycle[1]^reference_cycle[0], reference_cycle[2], !reference_cycle[0]};
  CheckpointResetOwnedClockCut #(.GATES(3),.OWNERS(4),.RESETS(2)) dut(
    .clock(clock),.controller_reset(controller_reset),.freeze_request(freeze_request),
    .ce(ce),.target_cycle(target_cycle),.owner_present(owner_present),
    .reset_writer_present(reset_writer_present),.reset_in(reset_in),
    .functional_reset(functional_reset),.root_clock(root_clock),.gate_clock(gate_clock),
    .clock_mask(clock_mask),.stopped(stopped),.read_enable(read_enable),.failed(failed),
    .captured_ce(captured_ce),.cut_cycle(cut_cycle),.physical_error(physical_error),
    .reset_error(reset_error),.captured_reset(captured_reset),.control_state(control_state));
  CheckpointResetOwnedClockCut #(.GATES(3),.OWNERS(4),.RESETS(2),.EXTERNAL_CLOCK_NETWORK(1)) peer(
    .clock(clock),.controller_reset(controller_reset),.freeze_request(freeze_request),
    .ce(ce),.target_cycle(target_cycle),.owner_present(owner_present),
    .reset_writer_present(reset_writer_present),.reset_in(reset_in),
    .functional_reset(external_reset),.root_clock(external_root),.gate_clock(external_gates),
    .clock_mask(external_mask),.read_enable(external_read),.failed(external_failed),
    .control_state(external_state));
  always @(posedge root_clock)
    if(controller_reset) target_cycle<=0; else target_cycle<=target_cycle+1;
  always @(posedge reference_clock)
    if(controller_reset) reference_cycle<=0; else reference_cycle<=reference_cycle+1;
  genvar g;
  generate for(g=0;g<3;g++) begin: refs
    BUFGCE gate(.I(reference_clock),.CE(reference_ce[g]),.O(reference_gate[g]));
    always @(posedge gate_clock[g])
      if(functional_reset[g%2]) state[g]<=g+1;
      else state[g]<=(state[g]*33)^(target_cycle+g);
    always @(posedge reference_gate[g])
      if(reference_reset[g%2]) expected_state[g]<=g+1;
      else expected_state[g]<=(expected_state[g]*33)^(reference_cycle+g);
  end endgenerate
  integer checks=0, cuts=0, stalls=0, cycle=0, k, j;
  reg [31:0] held_state[3];
  reg [1:0] saved_reset;
  string fault;
  bit corrupt;
  task check(input bit ok,input string why);
    checks++;
    if(!ok) begin
      $display("RESET_CUT_DIVERGENCE target_cycle=%0d reason=%s",target_cycle,why);
      $dumpflush; checkpoint_widget_failed(); $finish;
    end
  endtask
  task compare;
    check(target_cycle===reference_cycle,"independent cycle");
    check(functional_reset===reference_reset,"unmodified functional reset");
    check(external_state===control_state && external_reset===functional_reset &&
        external_read===read_enable && external_failed===failed && external_mask===clock_mask,
        "native external-network mode has identical cut state");
    check(external_root===0 && external_gates===0,"external mode instantiates no clock gates");
    for(integer i=0;i<3;i++) check(state[i]===expected_state[i],"gated reset/data state");
  endtask
  task step;
    clock=0;reference_clock=0;#3;clock=1;reference_clock=1;#3;
    if(!controller_reset) begin cycle++;check(target_cycle==cycle,"cycle label");compare();end
  endtask
  task held;
    check(stopped && clock_mask && root_clock===0 && gate_clock===0,"common cut stays stopped");
    check(target_cycle==cycle && cut_cycle==cycle,"cut label immutable");
    check(functional_reset===saved_reset && captured_reset===saved_reset,"reset cannot reach frozen state");
    check(external_state===control_state && external_reset===functional_reset &&
        external_read===read_enable && external_failed===failed && external_mask===clock_mask,
        "external mode agrees throughout hold and faults");
    for(integer i=0;i<3;i++) check(state[i]===held_state[i],"complete frozen words");
  endtask
  task capture;
    saved_reset=reset_in;freeze_request=1;#1;
    check(!read_enable,"request alone cannot acknowledge cut");
    clock=0;reference_clock=0;#3;
    check(stopped && !read_enable,"common low phase precedes acknowledgement");
    clock=1;#3;
    check(read_enable && !failed,"complete reset-owned cut");
    check(cut_cycle==cycle && captured_ce===reference_ce,"same-cut CE/cycle");
    for(integer i=0;i<3;i++) held_state[i]=state[i];
    held();cuts++;
    check(control_state[74:73]===saved_reset,"exact reset state layout");
    check(control_state[77:75]===0,"exact reset error layout");
    $display("RESET_CUT_CAPTURE target_cycle=%0d reset=%b ce=%b",cycle,captured_reset,captured_ce);
    if(corrupt && cycle==17)
      check(captured_reset===(saved_reset^1),"captured_reset[0]");
    if(fault!="" && cycle==17) begin
      // Arm release BEFORE introducing the last-half-cycle fault. A reset
      // change cannot exploit the core's previously validated release_pending.
      if(fault=="release-reset")begin
        freeze_request=0;clock=0;#3;clock=1;#3;
        check(stopped && !read_enable,"release validation keeps cut stopped");
      end
      if(fault=="reset0" || fault=="release-reset")reset_in=reset_in^1;
      else if(fault=="reset1")reset_in=reset_in^2;
      else if(fault=="writer")reset_writer_present=0;
      else if(fault=="owner")owner_present=7;
      else check(0,"unknown fault");
      #1;check(failed && !read_enable,"new fault immediately invalidates reads");
      freeze_request=0;
      clock=0;#3;check(stopped,"fault beats already validated release");
      clock=1;#3;
      check(|physical_error,"physical owner rejects invalid reset cut");
      if(fault!="owner")check(|reset_error,"reset fault retained");
      // Returning the writer to its old value cannot repair an invalid cut.
      reset_in=saved_reset;reset_writer_present=1;owner_present=15;
      repeat(12)begin clock=0;#3;clock=1;#3;held();check(failed && !read_enable,"sticky rejection");end
      $display("RESET_CUT_REJECT fault=%s target_cycle=17 acknowledged_edges=0",fault);
      $finish;
    end
    repeat(16)begin
      clock=0;#3;clock=1;#3;held();stalls++;
      check(read_enable && !failed,"ungated collection under backpressure");
    end
    freeze_request=0;#1;check(!read_enable,"withdraw before release edge");
    clock=0;#3;clock=1;#3;
    check(stopped && target_cycle==cycle,"registered release validation");
    clock=0;reference_clock=0;#3;
    check(!stopped && !read_enable,"common falling-edge release");
  endtask
  initial begin
    corrupt=$test$plusargs("corrupt");
    if(!$value$plusargs("fault=%s",fault))fault="";
    $dumpfile("reset-cut.vcd");$dumpvars(0,reset_owned_clock_cut_tb);
    #120;step();step();controller_reset=0;
    // An asserted functional reset is a legitimate early cut, never a
    // collector reset. It must not erase the clock mask or published label.
    capture();reset_in=0;reference_reset=0;
    for(k=1;k<=256;k++)begin
      // Exercise both reset writers in ordinary running execution. The
      // reference receives the original values with no added pipeline edge.
      if(k==60 || k==140)begin reset_in=2;reference_reset=2;end
      if(k==62 || k==142)begin reset_in=0;reference_reset=0;end
      step();if(k==17 || k==128 || k==256)capture();
    end
    for(k=0;k<64;k++)step();
    check(cuts==4 && stalls==64 && cycle==320,"full cut and resumed scope");
    $display("RESET_CUT_PASS checks=%0d cycles=%0d cuts=%0d stalls=%0d",checks,cycle,cuts,stalls);
    $finish;
  end
endmodule
