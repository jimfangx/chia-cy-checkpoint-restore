`timescale 1ns/1ps
// Independent original vendor gate + arithmetic/state scoreboard. Vendor
// internal references below are test observations, never capture wiring.
module physical_clock_cut_tb;
  import "DPI-C" function void checkpoint_network_fail();
  localparam integer N = 3;
  reg clock=0, reference_clock=0, reset=1, freeze_request=0;
  reg [3:0] owner_present=15;
  reg [N-1:0] ce_corruption=0;
  reg [63:0] cycle_corruption=0;
  wire root_clock, stopped, read_enable, failed;
  wire [N-1:0] gate_clock, captured_ce;
  wire [63:0] cut_cycle;
  wire [2:0] error;
  reg [63:0] target_cycle=0, reference_cycle=0;
  reg [31:0] state [N-1:0];
  reg [31:0] reference_state [N-1:0];
  wire [N-1:0] reference_gate;
  wire [N-1:0] ce = reset ? 3'b111 : {target_cycle[1] ^ target_cycle[0], target_cycle[2], !target_cycle[0]};
  wire [N-1:0] reference_ce = reset ? 3'b111 : {reference_cycle[1] ^ reference_cycle[0], reference_cycle[2], !reference_cycle[0]};
  CheckpointPhysicalClockCut #(.GATES(N), .OWNERS(4)) dut(
    .clock(clock), .reset(reset), .freeze_request(freeze_request),
    .ce(ce ^ ce_corruption), .target_cycle(target_cycle ^ cycle_corruption), .owner_present(owner_present),
    .root_clock(root_clock), .gate_clock(gate_clock), .stopped(stopped),
    .read_enable(read_enable), .failed(failed), .captured_ce(captured_ce), .cut_cycle(cut_cycle), .error(error));
  always @(posedge root_clock) if (reset) target_cycle <= 0; else target_cycle <= target_cycle+1;
  always @(posedge reference_clock) if (reset) reference_cycle <= 0; else reference_cycle <= reference_cycle+1;
  genvar g;
  generate for (g=0;g<N;g=g+1) begin : ref_gates
    BUFGCE gate(.I(reference_clock), .CE(reference_ce[g]), .O(reference_gate[g]));
    always @(posedge gate_clock[g]) if (reset) state[g] <= g+1;
      else state[g] <= (state[g]*33) ^ (target_cycle+g);
    always @(posedge reference_gate[g]) if (reset) reference_state[g] <= g+1;
      else reference_state[g] <= (reference_state[g]*33) ^ (reference_cycle+g);
  end endgenerate
  integer checks=0, cuts=0, stalls=0, cycle=0, k, j, edge_counts[N-1:0];
  reg [63:0] saved_cycle;
  reg [31:0] saved_state[N-1:0];
  reg corrupt;
  string fault;
  always @(posedge gate_clock[0]) edge_counts[0]++;
  always @(posedge gate_clock[1]) edge_counts[1]++;
  always @(posedge gate_clock[2]) edge_counts[2]++;
  task check(input bit ok, input string reason);
    checks++;
    if (!ok) begin
      $display("PHYSICAL_CUT_DIVERGENCE target_cycle=%0d reason=%s",target_cycle,reason);
      checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task compare;
    check(target_cycle===reference_cycle,"root cycle");
    for (integer i=0;i<N;i++) check(state[i]===reference_state[i],"original gated functional state");
  endtask
  // Both clocks start/end high. CE changes produced by root registers during
  // the high phase must be captured AFTER the next stopped low phase.
  task step;
    clock=0; reference_clock=0; #3;
    clock=1; reference_clock=1; #3;
    if (!reset) begin
      cycle++;
      check(target_cycle==cycle,"independent target cycle label");
      compare();
    end
  endtask
  task capture;
    freeze_request=1;
    #1; check(!read_enable,"no premature read before falling cut");
    clock=0; reference_clock=0; #3;
    check(stopped && !read_enable,"mask established before snapshot");
    check(root_clock===0 && gate_clock===0,"all native outputs low");
    clock=1; #3;
    check(read_enable && !failed,"snapshot valid only after stopped low phase");
    check(cut_cycle==cycle && target_cycle==cycle,"atomic cycle identity");
    check(captured_ce===reference_ce,"complete logical enable vector");
    check(captured_ce[0]===ref_gates[0].gate.enable_clk &&
          captured_ce[1]===ref_gates[1].gate.enable_clk &&
          captured_ce[2]===ref_gates[2].gate.enable_clk,"independent vendor low-latch readback");
    check(dut.internal_clock_network.root_gate.enable_clk===0 && dut.internal_clock_network.gates[0].gate.enable_clk===0 &&
          dut.internal_clock_network.gates[1].gate.enable_clk===0 && dut.internal_clock_network.gates[2].gate.enable_clk===0,
          "physical latch is masked, logical mapping is separate");
    if (corrupt && cycle==17) check(captured_ce===(reference_ce ^ 1),"captured_ce[0]");
    saved_cycle=target_cycle;
    for (integer i=0;i<N;i++) saved_state[i]=state[i];
    cuts++;
    $display("PHYSICAL_CUT_CAPTURE target_cycle=%0d captured_ce=%b output=0",cycle,captured_ce);
    if (fault!="" && cycle==17) begin
      if (fault=="missing") owner_present=7;
      else if (fault=="ce") ce_corruption=1;
      else if (fault=="cycle") cycle_corruption=1;
      else check(0,"unknown fault");
      #1; check(failed && !read_enable,"new fault suppresses permission immediately");
      freeze_request=0;
      clock=0; #3; clock=1; #3;
      check(|error,"fault retained");
      freeze_request=0;
      repeat(8) begin
        clock=0; #3; clock=1; #3;
        check(stopped && failed && !read_enable && target_cycle==saved_cycle,"failed cut cannot resume");
        for (integer i=0;i<N;i++) check(state[i]===saved_state[i],"failed state immutable");
      end
      $display("PHYSICAL_CUT_REJECT fault=%s target_cycle=17 acknowledged_edges=0 error=%b",fault,error);
      $finish;
    end
    // Transport progresses while every functional owner remains stopped.
    repeat(16) begin
      clock=0; #3; clock=1; #3; stalls++;
      check(read_enable && !failed && target_cycle==saved_cycle,"stable cut during backpressure");
      check(root_clock===0 && gate_clock===0 && cut_cycle==saved_cycle,"no functional pulses");
      for (integer i=0;i<N;i++) check(state[i]===saved_state[i],"all frozen state words");
    end
    freeze_request=0; #1;
    check(!read_enable,"release withdraws permission before any functional edge");
    // One ungated validation edge must precede the falling-edge unmask.
    clock=0; #3;
    check(stopped,"release waits for registered fault validation");
    clock=1; #3;
    check(stopped && !read_enable && target_cycle==saved_cycle,"release validation has no functional edge");
  endtask
  initial begin
    corrupt=$test$plusargs("corrupt");
    if (!$value$plusargs("fault=%s",fault)) fault="";
    for(j=0;j<N;j++) edge_counts[j]=0;
    $dumpfile("physical-cut.vcd"); $dumpvars(0,physical_clock_cut_tb);
    // Keep the vendor's unmodified glbl startup behavior.
    #120;
    step(); step(); reset=0;
    capture();
    for(k=1;k<=256;k++) begin
      step();
      if(k==17 || k==128 || k==256) capture();
    end
    // Release the late cut and exercise resumed traffic beyond that cut.
    for(k=0;k<64;k++) step();
    check(cuts==4 && stalls==64 && cycle==320,"complete cuts and continued traffic");
    for(j=0;j<N;j++) check(edge_counts[j]>60,"each gate active");
    $display("PHYSICAL_CUT_PASS checks=%0d cycles=%0d cuts=%0d stalls=%0d",checks,cycle,cuts,stalls);
    $finish;
  end
endmodule
