`timescale 1ns/1ps
// Component model audit only. Vendor/internal references are verification
// observations, never an FPGA capture path or a checkpoint readout adapter.
module bufgce_contract_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, ce=0;
  wire physical_o, abstract_o, metasim_o, hardsync_o;
  BUFGCE physical(.I(clock), .CE(ce), .O(physical_o));
  BUFGCE #(.CE_TYPE("HARDSYNC")) hardsync(.I(clock), .CE(ce), .O(hardsync_o));
  AbstractClockGate abstract_gate(.I(clock), .CE(ce), .O(abstract_o));
  CheckpointMetasimBUFGCE metasim(.I(clock), .CE(ce), .O(metasim_o));
  integer physical_edges=0, abstract_edges=0, metasim_edges=0, hardsync_edges=0;
  integer checks=0, source_edges=0, expected_physical=0, expected_abstract=0;
  integer high_changes=0, low_changes=0, cuts=0, abs_only_pulses=0;
  bit old_enable=0;
  bit corrupt=0;
  always @(posedge physical_o) physical_edges++;
  always @(posedge abstract_o) abstract_edges++;
  always @(posedge metasim_o) metasim_edges++;
  always @(posedge hardsync_o) hardsync_edges++;

  task check(input bit ok, input string reason);
    checks++;
    if (!ok) begin
      $display("BUFGCE_CONTRACT_MISMATCH source_edge=%0d checks=%0d reason=%s", source_edges, checks, reason);
      checkpoint_network_fail();
    end
  endtask
  task cut(input string phase);
    cuts++;
    $display("BUFGCE_CONTRACT_CUT source_edge=%0d phase=%s I=%b CE=%b O=%b vendor_enable=%b abstract_enable=%b physical_edges=%0d abstract_edges=%0d",
      source_edges, phase, clock, ce, physical_o, physical.enable_clk, abstract_gate.enable, physical_edges, abstract_edges);
    check(physical_o === (clock && physical.enable_clk), "vendor latch/output identity");
    check(metasim_o === physical_o, "metasim settled output");
  endtask
  task tick(input bit next_ce, input bit change_high);
    integer before_physical, before_abstract;
    bit predicted;
    check(clock===0, "source starts low");
    ce=next_ce; low_changes++; #2;
    check(physical.enable_clk === ce, "SYNC CE latch follows throughout low phase");
    cut("low");
    before_physical=physical_edges; before_abstract=abstract_edges;
    expected_physical += next_ce;
    expected_abstract += old_enable || next_ce;
    predicted=next_ce;
    if (corrupt && source_edges==3) predicted=~predicted;
    clock=1; source_edges++; #2;
    check(physical_o===predicted, "independent physical rising output");
    check(physical_edges==expected_physical && physical_edges==before_physical+next_ce,
      "physical positive edges");
    check(abstract_edges==expected_abstract && abstract_edges==before_abstract+(old_enable || next_ce),
      "abstract positive edges including old-enable pulse");
    if (old_enable && !next_ce) begin
      abs_only_pulses++;
      check(abstract_edges==before_abstract+1 && physical_edges==before_physical,
        "abstract-only pulse on CE deassertion");
    end
    old_enable=next_ce;
    check(physical_o===next_ce && abstract_o===next_ce, "settled output hides extra abstract edge");
    if (change_high) begin
      ce=~ce; high_changes++; #2;
      check(physical.enable_clk===next_ce && physical_o===next_ce,
        "SYNC CE latch holds through high phase");
      cut("high_changed_ce");
      ce=next_ce; #2;
    end
    check(physical_edges==metasim_edges, "metasim edge count for stable edge inputs");
    cut("high");
    clock=0; #2;
    check(physical_o===0 && metasim_o===0 && abstract_o===0, "falling outputs");
  endtask
  integer i;
  initial begin
    corrupt=$test$plusargs("corrupt");
    $dumpfile("bufgce-contract.vcd"); $dumpvars(0,bufgce_contract_tb);
    // Native glbl's real default startup reset lasts 100 ns.
    #120;
    clock=1; #2; clock=0; #2;
    // Initialize the abstract implementation's unreset register before the
    // counted experiment. The native primitive has its own startup behavior.
    check(abstract_gate.enable===0 && physical.enable_clk===0, "initialized CE owners");
    physical_edges=0; abstract_edges=0; metasim_edges=0; hardsync_edges=0;
    for (i=0;i<256;i++) begin
      tick((i%7==0 || i%7==1 || i%7==4), i%3!=0);
    end
    check(source_edges==256 && cuts>=512 && abs_only_pulses>50 && high_changes>100,
      "complete phase and CE transition scope");
    check(physical_edges==metasim_edges && abstract_edges>physical_edges,
      "distinct abstract contract");
    $display("BUFGCE_CONTRACT_PASS checks=%0d source_edges=%0d cuts=%0d physical_edges=%0d abstract_edges=%0d metasim_edges=%0d hardsync_edges=%0d abstract_only_pulses=%0d high_changes=%0d low_changes=%0d",
      checks,source_edges,cuts,physical_edges,abstract_edges,metasim_edges,hardsync_edges,abs_only_pulses,high_changes,low_changes);
    $finish;
  end
endmodule
