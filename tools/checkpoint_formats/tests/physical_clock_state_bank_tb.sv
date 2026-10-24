`timescale 1ns/1ps
// Generated bank RTL, compiler-generated clocks and original native SYNC gates.
module physical_clock_state_bank_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, reset=1, freeze_request=0;
  always #5 clock=!clock;
  wire [63:0] target_cycle;
  wire [31:0] state0, state1, state2;
  wire [2:0] ce, captured_ce, error;
  wire clock_mask, stopped, read_enable, failed, root_clock;
  wire [2:0] gate_clock;
  wire [63:0] cut_cycle;
  PhysicalTransportNetwork network(.clock(clock),.reset(reset),.target_cycle(target_cycle),
    .state0(state0),.state1(state1),.state2(state2),.checkpoint_physical_mask(clock_mask),
    .checkpoint_physical_logical_ce(ce));
  CheckpointPhysicalClockCut #(.GATES(3),.OWNERS(1),.EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock),.reset(reset),.freeze_request(freeze_request),.ce(ce),.target_cycle(target_cycle),
    .owner_present(1'b1),.root_clock(root_clock),.gate_clock(gate_clock),.clock_mask(clock_mask),
    .stopped(stopped),.read_enable(read_enable),.failed(failed),.captured_ce(captured_ce),
    .cut_cycle(cut_cycle),.error(error));
  reg [31:0] descriptor_entry=0;
  wire descriptor_valid;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth;
  reg request_valid=0, response_ready=0;
  wire request_ready, response_valid, response_error;
  reg [7:0] bank=255;
  reg [15:0] slot=0;
  reg [31:0] address=0;
  wire [63:0] response_data;
  `CE_BANK_MODULE endpoint(.*);
  integer checks=0, cuts=0, reads=0, stalls=0;
  reg [63:0] expected_cycle=0;
  reg [31:0] expected_state[0:2];
  reg [2:0] oracle_ce;
  reg [2:0] seen_one=0, seen_zero=0;
  reg [63:0] saved_cycle;
  reg [31:0] saved_state[0:2];
  string fault;
  bit corrupt;
  task check(input bit ok, input string message);
    checks++;
    if(!ok) begin
      $display("PHYSICAL_CE_BANK_DIVERGENCE target_cycle=%0d reason=%s acknowledged_edges=0",target_cycle,message);
      checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task tick; @(posedge clock); #2; endtask
  task submit(input [7:0] b, input [15:0] s, input [31:0] a);
    @(negedge clock); #1;
    bank=b; slot=s; address=a; request_valid=1;
    check(request_ready,"endpoint available");
    tick;
    check(response_valid,"response follows accepted read");
    request_valid=0;
    reads++;
  endtask
  task drain;
    @(negedge clock); #1; response_ready=1;
    tick; check(!response_valid,"drained response");
    response_ready=0;
  endtask
  task held(input [63:0] data, input bit err);
    repeat(7) begin
      // Request mutations while blocked must never replace the accepted beat.
      @(negedge clock); #1; bank=0; slot=65535; address=32'hffffffff; request_valid=1;
      tick;
      check(!request_ready && response_valid && response_data===data && response_error===err,
            "stable full response under backpressure");
      stalls++;
    end
    request_valid=0;
  endtask
  task snapshot(input integer at_cycle);
    while(target_cycle<at_cycle) begin @(negedge clock); #1; end
    freeze_request=1;
    while(!read_enable) tick;
    saved_cycle=expected_cycle;
    for(integer i=0;i<3;i++) saved_state[i]=expected_state[i];
    oracle_ce={saved_cycle[1]^saved_cycle[0],saved_cycle[2],!saved_cycle[0]};
    seen_one=seen_one | oracle_ce;
    seen_zero=seen_zero | ~oracle_ce;
    check(cut_cycle==saved_cycle && captured_ce===oracle_ce,"independent physical sample");
    for(integer i=0;i<3;i++) begin
      descriptor_entry=i; #1;
      check(descriptor_valid && descriptor_bank==255 && descriptor_slot==i &&
            descriptor_width==1 && descriptor_depth==1,"per-StateID descriptor shape and order");
      submit(255,i,0);
      check(!response_error && response_data==((oracle_ce>>i)&1),"physical CE word");
      held((oracle_ce>>i)&1,0);
      drain;
    end
    if(corrupt) begin
      submit(255,0,0);
      check(response_data==!oracle_ce[0],"deliberately corrupt CE oracle");
    end
    submit(254,0,0); check(response_error && response_data==0,"foreign bank rejects"); drain;
    submit(255,3,0); check(response_error && response_data==0,"missing physical owner slot rejects"); drain;
    submit(255,65535,0); check(response_error && response_data==0,"slot cannot wrap"); drain;
    submit(255,0,1); check(response_error && response_data==0,"nonzero address rejects"); drain;
    submit(255,0,32'hffffffff); check(response_error && response_data==0,"address cannot wrap"); drain;
    check(target_cycle==saved_cycle && state0==saved_state[0] && state1==saved_state[1] && state2==saved_state[2],
          "readout acknowledges zero functional edges");
    // Complete response remains latched while the cut releases. Further reads
    // outside an acknowledged cut must fail, including a pipelined replacement.
    submit(255,2,0);
    freeze_request=0;
    while(stopped) tick;
    held((oracle_ce>>2)&1,0);
    @(negedge clock); #1;
    request_valid=1; bank=255; slot=0; address=0; response_ready=1;
    tick;
    check(response_valid && response_error && response_data==0,"replacement without cut rejects");
    request_valid=0; response_ready=0; reads++;
    drain;
    cuts++;
  endtask
  always @(posedge clock) begin
    if(reset) begin
      expected_cycle=0;
      for(integer i=0;i<3;i++) expected_state[i]=i+1;
    end else begin
      if(!stopped) begin
        if(!expected_cycle[0]) expected_state[0]=(expected_state[0]*33)^expected_cycle;
        if(expected_cycle[2]) expected_state[1]=(expected_state[1]*33)^(expected_cycle+1);
        if(expected_cycle[1]^expected_cycle[0]) expected_state[2]=(expected_state[2]*33)^(expected_cycle+2);
        expected_cycle++;
      end
      #1;
      check(target_cycle==expected_cycle,"independent resumed root cycles");
      check(state0===expected_state[0] && state1===expected_state[1] && state2===expected_state[2],
            "independent resumed gated workload");
      check(!failed,"physical sampler remains healthy");
    end
  end
  initial begin
    $dumpfile("physical-ce-bank.vcd"); $dumpvars(0,physical_clock_state_bank_tb);
    corrupt=$test$plusargs("corrupt");
    repeat(14) tick;
    @(negedge clock); #1; reset=0;
    // Invalid descriptors must not alias the first owner.
    for(integer i=3;i<6;i++) begin
      descriptor_entry=i==5 ? 32'hffffffff : i; #1;
      check(!descriptor_valid && descriptor_bank==0 && descriptor_slot==0 && descriptor_width==0 && descriptor_depth==0,
            "invalid descriptor rejects without alias");
    end
    submit(255,0,0); check(response_error && response_data==0,"read before freeze rejects"); drain;
    snapshot(2); snapshot(21); snapshot(128); snapshot(256);
    // Reset must cancel a held accepted response, including immediately
    // removing request readiness before the reset edge.
    submit(255,0,0);
    @(negedge clock); #1; reset=1; request_valid=1; #1;
    check(!request_ready,"reset suppresses request acceptance");
    tick; check(!response_valid && response_data==0 && !response_error,"reset cancels held response");
    request_valid=0; repeat(3) tick;
    @(negedge clock); #1; reset=0;
    snapshot(2);
    while(target_cycle<320) tick;
    check(cuts==5 && stalls==140,"complete cut and backpressure scope");
    check(seen_one==7 && seen_zero==7,"every physical CE bit observed both zero and one");
    $display("PHYSICAL_CE_BANK_COVERAGE ones=%0d zeros=%0d",seen_one,seen_zero);
    $display("PHYSICAL_CE_BANK_PASS checks=%0d cuts=%0d reads=%0d stalls=%0d cycles=%0d",checks,cuts,reads,stalls,target_cycle);
    $finish;
  end
  initial begin #200000; $fatal(1,"physical CE bank timeout"); end
endmodule
