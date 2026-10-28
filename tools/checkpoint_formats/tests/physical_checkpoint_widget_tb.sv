`timescale 1ns/1ps
module physical_checkpoint_widget_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock = 0; always #5 clock = ~clock;
  reg reset = 1;
  reg awvalid=0, wvalid=0, arvalid=0, bready=0, rready=0;
  reg [31:0] awaddr=0, araddr=0, wdata=0;
  reg [7:0] awlen=0, arlen=0;
  reg [2:0] awsize=2, arsize=2;
  reg [3:0] awid=3, arid=9, strb=15;
  reg wlast=1;
  wire awready, wready, arready, bvalid, rvalid;
  wire [1:0] bresp, rresp;
  wire [3:0] bid, rid;
  wire [31:0] rdata;
  wire rlast, requestValid, requestWrite, responseReady;
  wire [7:0] requestAddress;
  wire [31:0] requestData;
  reg requestReady=1, responseValid=0, responseError=0;
  reg [31:0] responseData=0;
  integer commands=0, checks=0, timeout=0;
  wire controllerReset, freeze, bankValid, bankResponseReady, streamValid, streamLast, streamAbort;
  wire [31:0] entry, address;
  wire [7:0] bank;
  wire [15:0] slot;
  wire [511:0] streamData;
  reg [1:0] ownerPresent=3;
  reg streamReady=0;
  wire [63:0] target_cycle;
  wire [31:0] state[0:2];
  wire [2:0] network_ce, captured_ce, physical_error;
  wire [2:0] logical_ce={target_cycle[1]^target_cycle[0],target_cycle[2],!target_cycle[0]};
  reg [2:0] ce_fault=0;
  reg [63:0] cycle_fault=0;
  wire clock_mask, physical_stopped, physical_read_enable, physical_failed;
  wire [63:0] physical_cut_cycle;
  wire [31:0] descriptor_entry=entry;
  wire descriptor_valid;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth;
  wire bank_request_valid=bankValid, bank_response_ready=bankResponseReady;
  wire bank_request_ready, bank_response_valid, bank_response_error;
  wire [63:0] bank_response_data;
  reg functional_response_valid=0;
  wire functional_response_error=0;
  reg [63:0] functional_response_data=0;
  integer bankDelay=0, frames=0, words=0, cuts=0, fd=0, stalls=0, step=0;
  wire functional_request_ready=!functional_response_valid && bankDelay==0;
  reg [63:0] expected_cycle=0, saved_cycle=0, accepted_cycle=0;
  reg [31:0] expected_state[0:2], saved_state[0:2];
  reg [2:0] saved_ce;
  reg [511:0] heldFrame;
  reg stalled=0, corrupt=0;
  string fault, frames_path;
  reg [1241:0] shadow_expected;
  integer shadow_captures=0,shadow_word_checks=0,sw;
  reg [63:0] shadow_word;
  always @(posedge clock) begin
    if(!reset && dut.adapter.io_request_valid && dut.adapter.io_request_ready &&
       dut.adapter.io_request_bits_write && dut.adapter.io_request_bits_address=='h78 &&
       dut.adapter.io_request_bits_data==1 && !dut.snapshot.io_error) begin
      shadow_expected={dut.adapter.errorReadRemaining,
        {60'b0,dut.adapter.responseId},
        dut.adapter.responseData,
        dut.adapter.responseError,
        dut.adapter.responseValid,
        dut.adapter.writing,
        dut.adapter.busy,
        dut.adapter.badW,
        dut.adapter.haveAR,
        dut.adapter.haveW,
        dut.adapter.haveAW,
        dut.adapter.ar_user,
        {60'b0,dut.adapter.ar_id},
        dut.adapter.ar_region,
        dut.adapter.ar_qos,
        dut.adapter.ar_prot,
        dut.adapter.ar_cache,
        dut.adapter.ar_lock,
        dut.adapter.ar_burst,
        dut.adapter.ar_size,
        dut.adapter.ar_len,
        {32'b0,dut.adapter.ar_addr},
        dut.adapter.wd_user,
        dut.adapter.wd_strb,
        {60'b0,dut.adapter.wd_id},
        dut.adapter.wd_last,
        dut.adapter.wd_data,
        dut.adapter.aw_user,
        {60'b0,dut.adapter.aw_id},
        dut.adapter.aw_region,
        dut.adapter.aw_qos,
        dut.adapter.aw_prot,
        dut.adapter.aw_cache,
        dut.adapter.aw_lock,
        dut.adapter.aw_burst,
        dut.adapter.aw_size,
        dut.adapter.aw_len,
        {32'b0,dut.adapter.aw_addr},
        dut.localError,
        dut.localData,
        dut.localValid,
        dut.counterOverflow,
        dut.hostDrainedFrames,
        dut.producedSnapshot,
        dut.producedFrames,
        dut.invalid,
        dut.transport_physicalTransport.physical.error,
        dut.transport_physicalTransport.physical.cut_cycle,
        dut.transport_physicalTransport.physical.captured_ce,
        dut.transport_physicalTransport.physical.release_pending,
        dut.transport_physicalTransport.physical.sampled,
        dut.transport_physicalTransport.physical.freeze_low,
        dut.transport_physicalTransport.transport.cut.error,
        dut.transport_physicalTransport.transport.cut.cut_cycle,
        dut.transport_physicalTransport.transport.cut.state,
        dut.transport_physicalTransport.transport.address,
        dut.transport_physicalTransport.transport.descriptor_entry,
        dut.transport_physicalTransport.transport.mmio_response_error,
        dut.transport_physicalTransport.transport.mmio_rdata,
        dut.transport_physicalTransport.transport.mmio_response_valid,
        dut.transport_physicalTransport.transport.transport_error,
        dut.transport_physicalTransport.transport.outstanding,
        dut.transport_physicalTransport.transport.stream_crc,
        dut.transport_physicalTransport.transport.words,
        dut.transport_physicalTransport.transport.saved_data,
        dut.transport_physicalTransport.transport.saved_depth,
        dut.transport_physicalTransport.transport.saved_width,
        dut.transport_physicalTransport.transport.saved_slot,
        dut.transport_physicalTransport.transport.saved_bank,
        dut.transport_physicalTransport.transport.state};
      shadow_captures++;
    end
  end
  localparam [255:0] HASH=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef;
  PhysicalTransportNetwork network(.clock(clock),.reset(reset),.target_cycle(target_cycle),
    .state0(state[0]),.state1(state[1]),.state2(state[2]),
    .checkpoint_physical_mask(clock_mask),.checkpoint_physical_logical_ce(network_ce));
`include "physical_state_router_fixture.svh"
  CheckpointCaptureWidget dut (
    .clock(clock), .reset(reset),
    .io_ctrl_aw_valid(awvalid), .io_ctrl_aw_ready(awready),
    .io_ctrl_aw_bits_addr(awaddr), .io_ctrl_aw_bits_id(awid),
    .io_ctrl_aw_bits_len(awlen), .io_ctrl_aw_bits_size(awsize),
    .io_ctrl_aw_bits_burst(2'd1), .io_ctrl_aw_bits_lock(1'b0),
    .io_ctrl_aw_bits_cache(4'd0), .io_ctrl_aw_bits_prot(3'd0),
    .io_ctrl_aw_bits_qos(4'd0), .io_ctrl_aw_bits_region(4'd0), .io_ctrl_aw_bits_user(1'b0),
    .io_ctrl_w_valid(wvalid), .io_ctrl_w_ready(wready),
    .io_ctrl_w_bits_data(wdata), .io_ctrl_w_bits_id(4'd0),
    .io_ctrl_w_bits_last(wlast), .io_ctrl_w_bits_strb(strb), .io_ctrl_w_bits_user(1'b0),
    .io_ctrl_b_valid(bvalid), .io_ctrl_b_ready(bready), .io_ctrl_b_bits_id(bid), .io_ctrl_b_bits_resp(bresp),
    .io_ctrl_ar_valid(arvalid), .io_ctrl_ar_ready(arready),
    .io_ctrl_ar_bits_addr(araddr), .io_ctrl_ar_bits_id(arid),
    .io_ctrl_ar_bits_len(arlen), .io_ctrl_ar_bits_size(arsize),
    .io_ctrl_ar_bits_burst(2'd1), .io_ctrl_ar_bits_lock(1'b0),
    .io_ctrl_ar_bits_cache(4'd0), .io_ctrl_ar_bits_prot(3'd0),
    .io_ctrl_ar_bits_qos(4'd0), .io_ctrl_ar_bits_region(4'd0), .io_ctrl_ar_bits_user(1'b0),
    .io_ctrl_r_valid(rvalid), .io_ctrl_r_ready(rready), .io_ctrl_r_bits_id(rid),
    .io_ctrl_r_bits_data(rdata), .io_ctrl_r_bits_resp(rresp), .io_ctrl_r_bits_last(rlast),
    .streamToHostCPU_ready(streamReady), .streamToHostCPU_valid(streamValid), .streamToHostCPU_bits(streamData),
    .capture_controllerReset(controllerReset), .capture_targetCycle(target_cycle ^ cycle_fault),
    .capture_ownerPresent(ownerPresent), .capture_ownerFrozen({2{freeze}}), .capture_ownerError(2'b0),
    .capture_freeze(freeze), .capture_descriptorEntry(entry), .capture_descriptorValid(descriptor_valid),
    .capture_descriptorBank(descriptor_bank), .capture_descriptorSlot(descriptor_slot),
    .capture_descriptorWidth(descriptor_width), .capture_descriptorDepth(descriptor_depth),
    .capture_bankRequestValid(bankValid), .capture_bankRequestReady(bank_request_ready),
    .capture_bank(bank), .capture_slot(slot), .capture_address(address),
    .capture_bankResponseValid(bank_response_valid), .capture_bankResponseReady(bankResponseReady),
    .capture_bankResponseData(bank_response_data), .capture_bankResponseError(bank_response_error),
    .capture_streamLast(streamLast), .capture_streamAbort(streamAbort),
    .capture_physical_logicalCE(network_ce ^ ce_fault), .capture_physical_clockMask(clock_mask),
    .capture_physical_capturedCE(captured_ce), .capture_physical_stopped(physical_stopped),
    .capture_physical_readEnable(physical_read_enable), .capture_physical_failed(physical_failed),
    .capture_physical_cutCycle(physical_cut_cycle), .capture_physical_error(physical_error)
  );
  task tick; begin @(posedge clock); #1; end endtask
  task check(input bit cond, input string why); begin
    checks=checks+1; if (!cond) begin
      $display("PHYSICAL_WIDGET_DIVERGENCE target_cycle=%0d expected=%0d saved=%0d accepted=%0d reason=%s",target_cycle,expected_cycle,saved_cycle,accepted_cycle,why);
      $dumpflush;
      checkpoint_widget_failed(); $finish;
    end
  end endtask
  task aw(input [31:0] addr); begin
    @(negedge clock); awaddr=addr; awvalid=1;
    do tick(); while (!dut.adapter.haveAW);
    @(negedge clock); awvalid=0;
  end endtask
  task w(input [31:0] data, input bit last); begin
    @(negedge clock); wdata=data; wlast=last; wvalid=1;
    do begin @(posedge clock); end while (!wready);
    #1; @(negedge clock); wvalid=0;
  end endtask
  task ar(input [31:0] addr); begin
    @(negedge clock); araddr=addr; arvalid=1;
    do tick(); while (!dut.adapter.haveAR);
    @(negedge clock); arvalid=0;
  end endtask
  task b(input [1:0] expected); begin
    while (!bvalid) tick();
    repeat(4) begin tick(); check(bvalid && bresp==expected && bid==awid,"held B response"); end
    @(negedge clock); bready=1; tick(); @(negedge clock); bready=0;
  end endtask
  task r(input [1:0] expected, input bit last, input [31:0] data); begin
    while (!rvalid) tick();
    repeat(3) begin tick(); check(rvalid && rresp==expected && rid==arid && rlast==last,"held R response"); end
    if (expected==0) check(rdata==data,"read data");
    @(negedge clock); rready=1; tick(); @(negedge clock); rready=0;
  end endtask
  task command(input [31:0] value, input [1:0] expected); begin aw(0); w(value,1); b(expected); end endtask
  task readReg(input [31:0] offset, input [31:0] value); begin ar(offset); r(0,1,value); end endtask
  task shadowCommand(input [31:0] value, input [1:0] status); begin
    aw('h78); w(value,1); b(status);
  end endtask
  task readShadow; begin
    readReg('h88,1); readReg('h8c,saved_cycle[31:0]); readReg('h90,saved_cycle[63:32]);
    readReg('h98,2); readReg('h9c,1242); readReg('h94,20);
    for(sw=0;sw<20;sw++) begin
      aw('h7c); w(sw,1); b(0); shadow_word=shadow_expected>>(sw*64);
      readReg('h80,shadow_word[31:0]); readReg('h84,shadow_word[63:32]); shadow_word_checks++;
    end
  end endtask
  always @(posedge clock) begin
    step++;
    if(reset) begin
      expected_cycle=0;
      for(integer i=0;i<3;i++) expected_state[i]=i+1;
    end else begin
      if(dut.adapter.io_request_valid && dut.adapter.io_request_ready &&
         dut.adapter.io_request_bits_write && dut.adapter.io_request_bits_address==0 &&
         dut.adapter.io_request_bits_data==1 && dut.transport_physicalTransport.transport.idle_ready)
        accepted_cycle=expected_cycle;
      if(!physical_stopped) begin
        if(!expected_cycle[0]) expected_state[0]=(expected_state[0]*33)^expected_cycle;
        if(expected_cycle[2]) expected_state[1]=(expected_state[1]*33)^(expected_cycle+1);
        if(expected_cycle[1]^expected_cycle[0]) expected_state[2]=(expected_state[2]*33)^(expected_cycle+2);
        expected_cycle++;
      end
      #1;
      check(target_cycle==expected_cycle,"independent root edges");
      for(integer i=0;i<3;i++) check(state[i]===expected_state[i],"independent gated arithmetic");
      if(physical_stopped) check(freeze,"external owners held until physical release");
      if(physical_read_enable && fault=="") begin
        check(captured_ce===logical_ce,"unmasked CE identity");
        check(physical_cut_cycle==target_cycle,"physical cycle identity");
      end
    end
  end
  always @(posedge clock) begin
    if(controllerReset) begin bankDelay<=0; functional_response_valid<=0; stalled<=0; end
    else begin
      if(functional_response_valid && functional_response_ready) functional_response_valid<=0;
      if(functional_request_valid && functional_request_ready) begin
        check(physical_read_enable && freeze,"no functional bank access before stopped cut");
        check(address<3 && slot==0 && (bank==1 || bank==2),"functional selectors");
        bankDelay<=3;
        functional_response_data <= bank==1 ? target_cycle : {32'd0,state[address]};
      end
      if(bankDelay>0) begin bankDelay<=bankDelay-1; if(bankDelay==1) functional_response_valid<=1; end
      if(stalled && !streamAbort) check(streamValid && streamData==heldFrame,"stalled frame stability");
      stalled<=streamValid && !streamReady && !streamAbort;
      if(streamValid && !streamReady) begin stalls++; heldFrame<=streamData; end
      if(streamValid && streamReady) begin
        check(physical_read_enable && !streamAbort,"DMA requires acknowledged physical cut");
        check(streamData[63:0]==64'h3154504b434d5346 && streamData[159:96]==saved_cycle,"frame envelope/cycle");
        if(frames==0) check(streamData[95:80]==1 && streamData[511:256]==HASH,"header/manifest");
        else if(streamData[95:80]==2) begin
          check(streamData[223:160]==words,"word order");
          case(words)
            0: check(streamData[399:336]==saved_cycle,"banked cycle");
            1,2,3: check(streamData[399:336]==saved_state[words-1],"banked arithmetic state");
            4,5,6: check(streamData[399:336]==(((saved_ce>>(words-4))&1) ^ (corrupt && cuts==1 && words==4)),"banked CE state");
            default: check(0,"extra word");
          endcase
          words++;
        end else check(streamData[95:80]==3 && streamLast && words==7,"complete trailer");
        if(fd) $fdisplay(fd,"%0128h",streamData);
        frames++;
      end
    end
  end
  task snapshot(input integer requested);
    while(target_cycle<requested) tick();
    @(negedge clock); streamReady=0; frames=0; words=0;
    command(1,0);
    while(!physical_read_enable) tick();
    saved_cycle=expected_cycle; saved_ce=logical_ce;
    for(integer i=0;i<3;i++) saved_state[i]=expected_state[i];
    // The registered AXI backend presents START before the preceding falling
    // edge. The common mask therefore stops functional owners before the
    // accepting source posedge, unlike the direct-MMIO fixture's later setup.
    check(saved_cycle==accepted_cycle,"post-stop cut equals actual adapter command edge");
    check(physical_cut_cycle==saved_cycle,"sampled post-stop cycle");
    if(fault!="" && cuts==1) begin
      @(negedge clock);
      if(fault=="ce") ce_fault=1;
      else if(fault=="cycle") cycle_fault=1;
      else if(fault=="missing") ownerPresent=1;
      else check(0,"unknown fault");
      #2; check(!streamValid && !bankValid && !physical_read_enable,"fault suppresses read/publication");
      repeat(4) tick();
      check(physical_failed && freeze && streamAbort,"physical fault is sticky and stream invalid");
      shadowCommand(1,2); readReg('h88,0);
      command(4,0);
      repeat(8) begin tick(); check(target_cycle==saved_cycle && freeze,"failed cut acknowledges zero edges"); end
      readReg('h60,1);
      $display("PHYSICAL_WIDGET_REJECT fault=%s cycle=%0d acknowledged_edges=0",fault,saved_cycle);
      $finish;
    end
    readReg('h60,0); shadowCommand(1,0); readShadow();
    shadowCommand(1,2); // preserve occupied epoch, never resample
    repeat(6) tick();
    while(frames<9) begin
      @(negedge clock); streamReady=step%4==0;
      tick();
    end
    @(negedge clock); streamReady=0;
    repeat(5) begin tick(); check(target_cycle==saved_cycle && freeze,"publication stall preserves cut"); end
    readReg(4,10); readReg('h18,7); readReg('h20,5);
    readShadow(); shadowCommand(2,0); readReg('h88,0);
    command(2,0);
    while(physical_stopped || freeze) tick();
    cuts++;
    $display("PHYSICAL_WIDGET_CAPTURE requested=%0d accepted=%0d cut=%0d words=%0d",requested,accepted_cycle,saved_cycle,words);
  endtask
  initial begin
    if(!$value$plusargs("fault=%s",fault)) fault="";
    corrupt=$test$plusargs("corrupt");
    if($value$plusargs("frames=%s",frames_path)) begin fd=$fopen(frames_path,"w"); check(fd!=0,"frame log opened"); end
    $dumpfile("physical-widget.vcd"); $dumpvars(0,physical_checkpoint_widget_tb);
    #120; repeat(3) tick(); @(negedge clock); reset=0;
    // Abort a stalled unpublished stream through actual AXI, then enforce drain ack.
    command(1,0); while(!streamValid) tick();
    command(4,0); while(freeze || physical_stopped) tick();
    readReg('h60,1); command(1,2);
    aw('h64); w(1,1); b(0); readReg('h60,0);
    snapshot(0); snapshot(80); snapshot(160); snapshot(240); snapshot(320);
    while(target_cycle<400) tick();
    readReg('h68,45); readReg('h6c,0);
    check(cuts==5 && stalls>50,"complete cuts and DMA backpressure");
    // Reset while a new header is stalled; no stale stream or endpoint may survive.
    command(1,0); while(!streamValid) tick();
    @(negedge clock); reset=1; #1;
    check(streamAbort && !streamValid && !bankValid && !physical_read_enable,"reset invalidates unpublished stream immediately");
    repeat(4) tick();
    check(!freeze && !physical_failed && !bank_response_valid,"common reset cancels all owners");
    @(negedge clock); reset=0; frames=0; words=0;
    snapshot(17);
    while(target_cycle<96) tick();
    check(shadow_captures==6 && shadow_word_checks==240,"complete physical shadow readback");
    $display("PHYSICAL_WIDGET_SHADOW_PASS captures=%0d words=%0d",shadow_captures,shadow_word_checks);
    $display("PHYSICAL_WIDGET_PASS checks=%0d cuts=%0d stalls=%0d recovered_cycles=%0d",checks,cuts,stalls,target_cycle);
    if(fd) $fclose(fd);
    $finish;
  end
  initial begin #200000; check(0,"watchdog timeout"); end
endmodule
