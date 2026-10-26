`timescale 1ns/1ps
// Independent edge/arithmetic oracle, actual vendor gates and delayed bank IO.
module physical_capture_transport_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, reset=1;
  always #5 clock=!clock;
`ifdef GENERATED_TRANSPORT_NETWORK
  wire [63:0] target_cycle;
  wire [31:0] state[0:2];
`else
  reg [63:0] target_cycle=0;
  reg [31:0] state[0:2];
`endif
  wire [2:0] logical_ce=reset ? 7 : {target_cycle[1]^target_cycle[0],target_cycle[2],!target_cycle[0]};
`ifdef GENERATED_TRANSPORT_NETWORK
  wire [2:0] network_ce;
`endif
  reg [2:0] ce_fault=0;
  reg [63:0] cycle_fault=0;
  `ifdef GENERATED_TRANSPORT_NETWORK
  wire [2:0] ce=network_ce ^ ce_fault;
`else
  wire [2:0] ce=logical_ce ^ ce_fault;
`endif
  wire root_clock, clock_mask, freeze, physical_stopped, physical_read_enable, physical_failed;
  wire [2:0] gate_clock, captured_ce, physical_error;
  wire [63:0] physical_cut_cycle;
  reg [3:0] owner_present=15, owner_frozen=0, owner_error=0;
  reg mmio_valid=0, mmio_write=0, mmio_response_ready=1;
  wire mmio_ready, mmio_response_valid, mmio_response_error;
  reg [7:0] mmio_address=0;
  reg [31:0] mmio_wdata=0;
  wire [31:0] mmio_rdata, descriptor_entry;
  wire descriptor_valid=descriptor_entry<3;
  wire [7:0] descriptor_bank=descriptor_entry+1;
  wire [15:0] descriptor_slot=0;
  wire [15:0] descriptor_width=descriptor_entry==0 ? 64 : descriptor_entry==1 ? 32 : 3;
  wire [31:0] descriptor_depth=descriptor_entry==1 ? 3 : 1;
  wire bank_request_valid, bank_response_ready;
  reg bank_request_ready=0, bank_response_valid=0, bank_response_error=0;
  reg [63:0] bank_response_data=0;
  wire [7:0] bank;
  wire [15:0] slot;
  wire [31:0] address;
  wire dma_valid, dma_last, dma_abort;
  reg dma_ready=0;
  wire [511:0] dma_data;
  localparam [255:0] HASH=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef;
`ifdef GENERATED_TRANSPORT_NETWORK
  PhysicalTransportNetwork network(.clock(clock),.reset(reset),.target_cycle(target_cycle),
    .state0(state[0]),.state1(state[1]),.state2(state[2]),
    .checkpoint_physical_mask(clock_mask),.checkpoint_physical_logical_ce(network_ce));
  localparam EXTERNAL_NETWORK=1;
`else
  localparam EXTERNAL_NETWORK=0;
`endif
  // Corruption inputs are deliberately outside the trusted functional owner.
  CheckpointPhysicalCaptureTransport #(.OWNERS(4),.GATES(3),.ENTRIES(3),.EXTERNAL_CLOCK_NETWORK(EXTERNAL_NETWORK),.MANIFEST_SHA256(HASH)) dut(
    .target_cycle(target_cycle ^ cycle_fault), .control_state(), .*);
`ifndef GENERATED_TRANSPORT_NETWORK
  always @(posedge root_clock) if(reset) target_cycle<=0; else target_cycle<=target_cycle+1;
  genvar g;
  generate for(g=0;g<3;g=g+1) begin : functional
    always @(posedge gate_clock[g]) if(reset) state[g]<=g+1;
      else state[g]<=(state[g]*33)^(target_cycle+g);
  end endgenerate
`endif
  integer checks=0, step=0, cuts=0, frames=0, words=0, dma_stalls=0, requests=0, delays=0;
  integer owner_delay=0, bank_delay=0, pending=0, held=0, aborts=0;
  reg hold_bank=0, hold_dma=0, lose_owner=0;
  reg [63:0] expected_cycle=0, saved_cycle, accepted_cycle;
  reg [31:0] expected_state[0:2], saved_state[0:2];
  reg [2:0] saved_ce;
  reg [511:0] stalled_data;
  reg was_stalled=0;
  integer fd=0;
  string fault, frames_path, reset_at;
  reg corrupt=0;
  task check(input bit ok, input string reason);
    checks++;
    if(!ok) begin
      $display("PHYSICAL_TRANSPORT_DIVERGENCE target_cycle=%0d reason=%s",target_cycle,reason);
      checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task tick; @(posedge clock); #2; endtask
  task command(input [31:0] value, input bit bad);
    @(negedge clock); #1;
    mmio_valid=1; mmio_write=1; mmio_address=0; mmio_wdata=value;
    do begin @(posedge clock); end while(!mmio_ready);
    #2; check(mmio_response_valid && mmio_response_error===bad,"MMIO command response");
    @(negedge clock); #1; mmio_valid=0;
  endtask
  task wait_idle;
    while(physical_stopped || freeze || pending || bank_response_valid) tick;
    repeat(2) tick;
  endtask
  task snapshot(input integer at_cycle);
    while(target_cycle<at_cycle) begin @(negedge clock); #1; end
    frames=0; words=0;
    command(1,0);
    while(!physical_read_enable) tick;
    saved_cycle=expected_cycle; saved_ce=logical_ce;
    for(integer i=0;i<3;i++) saved_state[i]=expected_state[i];
    check(saved_cycle==accepted_cycle+1,"post-stop label differs from accepting edge");
    check(physical_cut_cycle==saved_cycle,"physical sampler cut identity");
    check(captured_ce===saved_ce,"captured logical CE words");
    // All other owners deliberately acknowledge later than the physical stop.
    check(!dut.transport.read_enable && owner_frozen!=15,"non-clock owners still pending");
    if(fault!="" && cuts==1) begin
      @(negedge clock); #1;
      if(fault=="missing") owner_present=7;
      else if(fault=="ce") ce_fault=1;
      else if(fault=="cycle") cycle_fault=1;
      else if(fault=="owner") owner_error=1;
      else if(fault=="lost") begin
        while(!dut.transport.read_enable) tick;
        @(negedge clock); #1; lose_owner=1; owner_frozen=7;
      end else check(0,"unknown fault");
      #1; check(!dma_valid && !bank_request_valid,"fault suppresses all new transfers");
      repeat(4) tick;
      check(dma_abort && freeze,"failed capture remains frozen");
      if(fault=="missing" || fault=="ce" || fault=="cycle") begin
        command(4,0);
        repeat(8) tick;
        check(physical_stopped && physical_failed,"physical fault cannot resume on host abort");
      end
      repeat(8) begin tick; check(target_cycle==saved_cycle,"failed cut acknowledges zero edges"); end
      $display("PHYSICAL_TRANSPORT_REJECT fault=%s target_cycle=%0d acknowledged_edges=0",fault,saved_cycle);
      $finish;
    end
    while(frames<7) tick;
    repeat(3) tick;
    check(words==5 && freeze && dut.transport.cut_complete,"complete stream held for host publication");
    repeat(8) begin tick; check(target_cycle==saved_cycle && freeze,"publication stall keeps cut"); end
    command(2,0);
    $display("PHYSICAL_TRANSPORT_CAPTURE requested=%0d accepted=%0d cut=%0d words=%0d",at_cycle,accepted_cycle,saved_cycle,words);
    cuts++;
    wait_idle;
  endtask
  // Independent arithmetic oracle advances once per unmasked source edge.
  // It never reads a capture bank, captured cycle, or internal vendor state.
  always @(posedge clock) begin
    step++;
    if(reset) begin
      expected_cycle=0;
      for(integer i=0;i<3;i++) expected_state[i]=i+1;
      owner_frozen<=0; owner_delay<=0;
    end else begin
      if(mmio_valid && mmio_ready && mmio_write && mmio_wdata==1 && dut.transport.idle_ready)
        accepted_cycle=expected_cycle;
      if(!physical_stopped) begin
        if(!expected_cycle[0]) expected_state[0]=(expected_state[0]*33)^expected_cycle;
        if(expected_cycle[2]) expected_state[1]=(expected_state[1]*33)^(expected_cycle+1);
        if(expected_cycle[1]^expected_cycle[0]) expected_state[2]=(expected_state[2]*33)^(expected_cycle+2);
        expected_cycle++;
      end
      if(freeze) begin
        owner_delay<=owner_delay+1;
        if(owner_delay>=7) owner_frozen<=lose_owner ? 7 : 15;
      end else begin owner_delay<=0; owner_frozen<=0; end
      #1;
      if(physical_stopped) check(freeze,"non-clock owner hold extends through physical release");
      check(target_cycle==expected_cycle,"independent root edge count");
      for(integer i=0;i<3;i++) check(state[i]===expected_state[i],"independent gated arithmetic state");
      if(physical_read_enable && fault=="") begin
        check(captured_ce===logical_ce,"logical enables remain captured");
        check(physical_cut_cycle==target_cycle,"physical label stable");
      end
    end
  end
  always @(negedge clock) begin
    #0.5;
    dma_ready=!hold_dma && step%5==0;
    bank_request_ready=!pending && !bank_response_valid && step%3!=0;
  end
  always @(posedge clock) if(reset) begin
    pending<=0; bank_response_valid<=0; was_stalled<=0;
  end else begin
    if(bank_request_valid && bank_request_ready) begin
      check(physical_read_enable && owner_frozen==15,"bank reads require complete physical/global cut");
      check(!pending && !bank_response_valid,"one outstanding bank request");
      pending<=1; bank_delay<=3+step%3; requests++;
      if(bank==1) bank_response_data<=target_cycle;
      else if(bank==2) bank_response_data<=state[address];
      else if(bank==3) bank_response_data<=captured_ce;
      else check(0,"unknown bank");
    end
    if(pending && !hold_bank) begin
      delays++;
      if(bank_delay==0) begin pending<=0; bank_response_valid<=1; end
      else bank_delay<=bank_delay-1;
    end
    if(bank_response_valid && bank_response_ready) bank_response_valid<=0;
    if(was_stalled && !dma_abort) check(dma_valid && dma_data===stalled_data,"DMA frame stable under backpressure");
    was_stalled<=dma_valid && !dma_ready && !dma_abort;
    if(dma_valid && !dma_ready) begin stalled_data<=dma_data; dma_stalls++; end
    if(dma_valid && dma_ready) begin
      check(physical_read_enable && owner_frozen==15 && !dma_abort,"DMA requires complete acknowledged cut");
      check(dma_data[159:96]==saved_cycle,"DMA label is post-stop target cycle");
      if(frames==0) check(dma_data[95:80]==1 && dma_data[511:256]==HASH,"header manifest binding");
      else if(dma_data[95:80]==2) begin
        check(dma_data[223:160]==words,"data sequence");
        case(words)
          0: check(dma_data[399:336]==saved_cycle,"banked cycle state");
          1,2,3: check(dma_data[399:336]==saved_state[words-1],"banked gated state");
          4: check(dma_data[399:336]==(corrupt && cuts==1 ? saved_ce^1 : saved_ce),"banked logical CE state");
          default: check(0,"extra state word");
        endcase
        words++;
      end else check(dma_last && words==5 && dma_data[95:80]==3,"complete trailer");
      if(fd) $fdisplay(fd,"%0128h",dma_data);
      frames++;
    end
  end
  initial begin
    if(!$value$plusargs("fault=%s",fault)) fault="";
    if(!$value$plusargs("reset_at=%s",reset_at)) reset_at="";
    corrupt=$test$plusargs("corrupt");
    if($value$plusargs("frames=%s",frames_path)) begin fd=$fopen(frames_path,"w"); check(fd!=0,"frame log opened"); end
    $dumpfile("physical-transport.vcd"); $dumpvars(0,physical_capture_transport_tb);
    #120; repeat(3) tick; @(negedge clock); #1; reset=0;
    if(reset_at!="") begin
      frames=0; words=0;
      // Stall accepted bank reads or DMA data to reset at the actual hazard.
      if(reset_at=="response") hold_bank=1;
      if(reset_at=="data") hold_dma=1;
      command(1,0);
      if(reset_at!="freeze") begin
        while(!physical_read_enable) tick;
        saved_cycle=expected_cycle; saved_ce=logical_ce;
        for(integer i=0;i<3;i++) saved_state[i]=expected_state[i];
      end
      if(reset_at=="freeze") begin while(!physical_stopped) tick; end
      else if(reset_at=="response") begin while(!pending) tick; end
      else if(reset_at=="data") begin
        // Allow the header, then hold a data frame under backpressure.
        hold_dma=0;
        while(dut.transport.state!=5) tick;
        hold_dma=1;
        while(dut.transport.state!=6) tick;
      end else if(reset_at=="publish" || reset_at=="release") begin
        while(frames<7) tick;
        repeat(3) tick;
        check(dut.transport.cut_complete,"reset test reached complete unpublished cut");
        if(reset_at=="release") command(2,0);
      end else check(0,"unknown reset phase");
      // Assert between source edges, including while a completed stream has
      // dropped read_enable. The host must see invalidation immediately.
      #1; reset=1; #1;
      check(dma_abort && !dma_valid && !bank_request_valid && !mmio_ready &&
            !physical_read_enable,"reset combinationally invalidates unpublished stream");
      repeat(4) tick;
      check(!physical_stopped && !physical_failed && !freeze && !pending &&
            !bank_response_valid && !mmio_response_valid,"common reset clears all capture and endpoint state");
      @(negedge clock); #1; reset=0; hold_bank=0; hold_dma=0;
      frames=0; words=0; cuts=0;
      snapshot(17);
      while(target_cycle<64) tick;
      $display("PHYSICAL_TRANSPORT_RESET_PASS phase=%s recovered_cuts=%0d cycles=%0d checks=%0d",reset_at,cuts,target_cycle,checks);
      $finish;
    end
    snapshot(0); snapshot(17); snapshot(128); snapshot(256);
    // Cancel a cut with an accepted bank request, then drain its old response
    // before starting the next cut. Previously complete streams remain intact.
    hold_bank=1; hold_dma=0; frames=0; words=0;
    command(1,0);
    while(!physical_read_enable) tick;
    saved_cycle=expected_cycle; saved_ce=logical_ce;
    for(integer i=0;i<3;i++) saved_state[i]=expected_state[i];
    while(!pending) tick;
    command(4,0); aborts++;
    check(dut.transport.state==10 && !dma_valid,"abort drains accepted response");
    command(1,1);
    repeat(8) tick;
    hold_bank=0;
    wait_idle;
    snapshot(300);
    while(target_cycle<320) tick;
    check(dma_stalls>50 && delays>50 && requests==26 && cuts==5,"full cut/backpressure/recovery scope");
    $display("PHYSICAL_TRANSPORT_PASS checks=%0d cuts=%0d requests=%0d dma_stalls=%0d bank_delays=%0d aborts=%0d cycles=%0d",checks,cuts,requests,dma_stalls,delays,aborts,target_cycle);
    if(fd) $fclose(fd);
    $finish;
  end
  initial begin #100000; check(0,"timeout"); end
endmodule
