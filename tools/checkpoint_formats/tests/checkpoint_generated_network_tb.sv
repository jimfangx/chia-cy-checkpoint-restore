`timescale 1ns/1ps
// Real generated storage -> immutable ROM -> Widget/NASTI -> DMA.
// All oracles use functional inputs/public handshakes, with no hierarchy reads.
module checkpoint_generated_network_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0; always #5 clock=~clock;
  reg reset=1, functionalReset=1, wen=0;
  reg [8:0] data=0;
  reg [2:0] addr=0;
  wire [8:0] result;
  wire freeze, controllerReset;
  reg [63:0] targetCycle=0;
  wire bankValid, bankReady, responseValid, responseReady, responseError;
  wire [63:0] responseData;
  wire [7:0] bank;
  wire [15:0] slot;
  wire [31:0] address, entry;
  reg [1:0] ownerPresent=3;
  reg corruptState=0;
  initial corruptState=$test$plusargs("corrupt-state");
  reg awvalid=0,wvalid=0,arvalid=0,bready=0,rready=0;
  reg [31:0] awaddr=0,wdata=0,araddr=0;
  wire awready,wready,arready,bvalid,rvalid,rlast;
  wire [1:0] bresp,rresp;
  wire [31:0] rdata;
  wire streamValid,streamLast,streamAbort;
  wire [511:0] streamData;
  wire streamReady;
  integer hostEdges=0,checks=0,frames=0,captures=0,stalls=0,bankReads=0,functionalEdges=0;
  integer frameFile=0,byteIndex,romIndex;
  reg [63:0] capturedCycle;
  reg wasFrozen=0,held=0;
  reg [511:0] heldFrame;
  reg [31:0] probeEntry=0;
  wire probeValid;
  wire [7:0] probeBank;
  wire [15:0] probeSlot,probeWidth;
  wire [31:0] probeDepth;
  `include "generated_network_bindings.svh"
  assign streamReady=(hostEdges%7==0 || hostEdges%7==3);
  Harness storage (
    .clock(clock),.reset(functionalReset),.data(data),.addr(addr),.wen(wen),.result(result),
    .ckpt_reset(controllerReset),.ckpt_freeze(freeze),.ckpt_req_valid(bankValid),.ckpt_req_ready(bankReady),
    .ckpt_bank(bank),.ckpt_slot(slot),.ckpt_address(address),
    .ckpt_resp_valid(responseValid),.ckpt_resp_ready(responseReady),
    .ckpt_resp_data(responseData),.ckpt_resp_error(responseError),.ckpt_match(),.ckpt_data()
  );
  CheckpointCaptureDescriptorROMProbe probe (
    .clock(clock),.reset(reset),.io_entry(probeEntry),.io_valid(probeValid),
    .io_bank(probeBank),.io_slot(probeSlot),.io_bitWidth(probeWidth),.io_depth(probeDepth)
  );
  CheckpointCaptureWidget dut (
    .clock(clock),.reset(reset),
    .io_ctrl_aw_valid(awvalid),.io_ctrl_aw_ready(awready),
    .io_ctrl_aw_bits_addr(awaddr),.io_ctrl_aw_bits_id(4'd3),.io_ctrl_aw_bits_len(8'd0),
    .io_ctrl_aw_bits_size(3'd2),.io_ctrl_aw_bits_burst(2'd1),.io_ctrl_aw_bits_lock(1'b0),
    .io_ctrl_aw_bits_cache(4'd0),.io_ctrl_aw_bits_prot(3'd0),.io_ctrl_aw_bits_qos(4'd0),
    .io_ctrl_aw_bits_region(4'd0),.io_ctrl_aw_bits_user(1'b0),
    .io_ctrl_w_valid(wvalid),.io_ctrl_w_ready(wready),.io_ctrl_w_bits_data(wdata),
    .io_ctrl_w_bits_id(4'd0),.io_ctrl_w_bits_last(1'b1),.io_ctrl_w_bits_strb(4'd15),.io_ctrl_w_bits_user(1'b0),
    .io_ctrl_b_valid(bvalid),.io_ctrl_b_ready(bready),.io_ctrl_b_bits_id(),.io_ctrl_b_bits_resp(bresp),
    .io_ctrl_ar_valid(arvalid),.io_ctrl_ar_ready(arready),
    .io_ctrl_ar_bits_addr(araddr),.io_ctrl_ar_bits_id(4'd9),.io_ctrl_ar_bits_len(8'd0),
    .io_ctrl_ar_bits_size(3'd2),.io_ctrl_ar_bits_burst(2'd1),.io_ctrl_ar_bits_lock(1'b0),
    .io_ctrl_ar_bits_cache(4'd0),.io_ctrl_ar_bits_prot(3'd0),.io_ctrl_ar_bits_qos(4'd0),
    .io_ctrl_ar_bits_region(4'd0),.io_ctrl_ar_bits_user(1'b0),
    .io_ctrl_r_valid(rvalid),.io_ctrl_r_ready(rready),.io_ctrl_r_bits_id(),
    .io_ctrl_r_bits_data(rdata),.io_ctrl_r_bits_resp(rresp),.io_ctrl_r_bits_last(rlast),
    .streamToHostCPU_ready(streamReady),.streamToHostCPU_valid(streamValid),.streamToHostCPU_bits(streamData),
    .capture_controllerReset(controllerReset),.capture_targetCycle(targetCycle),
    .capture_ownerPresent(ownerPresent),.capture_ownerFrozen({2{freeze}}),.capture_ownerError(2'b0),
    .capture_freeze(freeze),.capture_descriptorEntry(entry),
    // Deliberately incompatible external descriptor pins must have no influence
    // in generated-ROM mode. Only the generated binding drives the transport.
    .capture_descriptorValid(1'b0),.capture_descriptorBank(8'hff),.capture_descriptorSlot(16'hffff),
    .capture_descriptorWidth(16'hffff),.capture_descriptorDepth(32'hffffffff),
    .capture_bankRequestValid(bankValid),.capture_bankRequestReady(bankReady),
    .capture_bank(bank),.capture_slot(slot),.capture_address(address),
    .capture_bankResponseValid(responseValid),.capture_bankResponseReady(responseReady),
    // The negative run changes an actual stored word in transit, with otherwise
    // valid framing/CRC. The independent functional oracle must stop it.
    .capture_bankResponseData(responseData ^ (corruptState ? 64'd1 : 64'd0)),.capture_bankResponseError(responseError),
    .capture_streamLast(streamLast),.capture_streamAbort(streamAbort)
  );
  reg refHarness=0;
  reg [8:0] refCounter=0,refBank[0:2],refLeft=0,refRight=0,refMem[0:7];
  reg [1:0] refFSM=0;
  function automatic [63:0] oracle(input integer kind,input integer at);
    case(kind)
      0:oracle=refHarness;
      1:oracle=refCounter;
      2:oracle=refFSM;
      3:oracle=refBank[0];
      4:oracle=refBank[1];
      5:oracle=refBank[2];
      6:oracle=refLeft;
      7:oracle=refRight;
      8:oracle=refMem[at];
      default:begin $fatal(1,"unknown oracle"); oracle=0; end
    endcase
  endfunction
  task check(input bit condition,input string why);
    begin
      checks=checks+1;
      if(!condition) begin
        $display("NETWORK_FAIL %s cycle=%0d freeze=%0b frame=%0d",why,capturedCycle,freeze,frames);
        $fflush();
        // SP2 may return zero for $fatal. Make every checker failure visible
        // to the process controller too; DPI never reads or writes DUT state.
        checkpoint_network_fail();
        $fatal(1,"unreachable failure exit");
      end
    end
  endtask
  always @(posedge clock) begin
    // Readiness changes after the sampling edge, never in its active region.
    hostEdges<=hostEdges+1;
    if(reset) targetCycle<=0;
    else if(!freeze) targetCycle<=targetCycle+1;
    if(!freeze) begin
      functionalEdges=functionalEdges+1;
      refHarness=functionalReset?0:!refHarness;
      refCounter=functionalReset?0:refCounter+1;
      refFSM=functionalReset?0:((refFSM==2)?0:refFSM+1);
      refBank[0]=data; refBank[1]=data+1; refBank[2]=data+2;
      refLeft=functionalReset?0:data; refRight=functionalReset?0:data+1;
      if(wen) refMem[addr]=data;
    end
    if(!reset) begin
      if(freeze && !wasFrozen) capturedCycle=targetCycle;
      if(freeze) check(targetCycle===capturedCycle,"no edge while frozen");
      if(bankValid && bankReady) bankReads=bankReads+1;
      if(held) check(streamValid && streamData===heldFrame,"DMA frame stable under stall");
      held=streamValid && !streamReady;
      if(held) begin heldFrame=streamData; stalls=stalls+1; end
      if(streamValid && streamReady) begin
        check(frameFile!=0,"no unpublished stream");
        check(streamData[63:0]===64'h3154504b434d5346 && streamData[79:64]===16'd1,"frame ABI");
        check(streamData[159:96]===capturedCycle,"exact target cut label");
        if(frames==0) begin
          check(streamData[95:80]===16'd1 && streamData[255:224]===ENTRY_COUNT,"complete header");
          check(streamData[511:256]===MANIFEST_HASH,"independent manifest hash");
        end else if(frames<=WORD_COUNT) begin
          check(streamData[95:80]===16'd2 && streamData[223:160]===frames-1,"ordered word");
          check(streamData[255:224]===wordEntries[frames-1] && streamData[287:256]===wordAddresses[frames-1],"entry/address");
          check(streamData[303:288]===widths[wordEntries[frames-1]],"logical width");
          check(streamData[311:304]===banks[wordEntries[frames-1]] && streamData[327:312]===slots[wordEntries[frames-1]],"selectors");
          check(streamData[399:336]===oracle(kinds[wordEntries[frames-1]],wordAddresses[frames-1]),"functional-input state oracle");
          check(!streamLast,"no premature trailer");
        end else check(frames==WORD_COUNT+1 && streamLast && streamData[95:80]===16'd3,"unique complete trailer");
        for(byteIndex=0;byteIndex<64;byteIndex=byteIndex+1) $fwrite(frameFile,"%c",streamData[byteIndex*8+:8]);
        frames=frames+1;
      end
    end
    wasFrozen=freeze;
  end
  task tick; begin @(posedge clock); #1; end endtask
  task writeReg(input [31:0] offset,input [31:0] value,input [1:0] expected);
    begin
      @(negedge clock); awaddr=offset; awvalid=1;
      do begin @(posedge clock); end while(!awready);
      @(negedge clock); awvalid=0;
      repeat(2) tick();
      @(negedge clock); wdata=value; wvalid=1;
      do begin @(posedge clock); end while(!wready);
      @(negedge clock); wvalid=0;
      while(!bvalid) tick();
      repeat(3) begin tick(); check(bvalid && bresp==expected,"held MMIO write response"); end
      @(negedge clock); bready=1; tick(); @(negedge clock); bready=0;
    end
  endtask
  task readReg(input [31:0] offset,input [31:0] value);
    begin
      @(negedge clock); araddr=offset; arvalid=1;
      do begin @(posedge clock); end while(!arready);
      @(negedge clock); arvalid=0;
      while(!rvalid) tick();
      repeat(3) begin tick(); check(rvalid && rresp==0 && rlast && rdata===value,"held MMIO read response/data"); end
      @(negedge clock); rready=1; tick(); @(negedge clock); rready=0;
    end
  endtask
  task capture;
    begin
      frames=0; frameFile=$fopen($sformatf("cut%0d.bin",captures),"wb"); check(frameFile!=0,"open frames");
      writeReg(0,1,0); check(freeze,"start frozen");
      // Neither functional reset nor active writes may disturb the captured cut.
      functionalReset=1; wen=1; data=511; addr=0;
      while(frames<WORD_COUNT+2) tick();
      readReg(4,10); readReg('h18,WORD_COUNT); readReg('h20,ENTRY_COUNT);
      check(freeze,"freeze held through independent publication");
      $fclose(frameFile); frameFile=0;
      $display("NETWORK_CAPTURE cut=%0d target_cycle=%0d words=%0d",captures,capturedCycle,WORD_COUNT);
      writeReg(0,2,0); check(!freeze,"publish releases");
      captures=captures+1;
      functionalReset=0; wen=0;
    end
  endtask
  integer i;
  initial begin
    $dumpfile("network.vcd"); $dumpvars(0,checkpoint_generated_network_tb);
    repeat(3) tick(); @(negedge clock); reset=0;
    // Probe every ROM row independently, including ordinals whose low bits alias
    // valid entries. Invalid values must not silently select a valid descriptor.
    for(i=0;i<ENTRY_COUNT+3;i=i+1) begin
      probeEntry=(i<ENTRY_COUNT)?i:(i==ENTRY_COUNT?ENTRY_COUNT:(i==ENTRY_COUNT+1?32'h10000:32'hffffffff)); #1;
      if(i<ENTRY_COUNT) check(probeValid && probeBank==banks[i] && probeSlot==slots[i] && probeWidth==widths[i] && probeDepth==depths[i],"ROM binding");
      else check(!probeValid && {probeBank,probeSlot,probeWidth,probeDepth}==0,"ROM invalid ordinal");
    end
    for(i=0;i<8;i=i+1) begin @(negedge clock); wen=1; addr=i; data=100+i; tick(); end
    @(negedge clock); functionalReset=0;
    repeat(15) begin @(negedge clock); data=data+3; addr=addr+1; tick(); end
    capture();
    repeat(20) begin @(negedge clock); data=data+7; addr=addr+1; wen=1; tick(); end
    capture();
    // Missing owner must fail frozen before any header or bank read is issued.
    @(negedge clock); ownerPresent=1;
    writeReg(0,1,0); repeat(5) tick(); check(freeze && !streamValid && !bankValid,"missing owner fails without state");
    readReg(8,1); writeReg(0,4,0); check(!freeze,"abort releases failed cut");
    writeReg(0,1,2); // Invalid history cannot be reused without counted drain.
    writeReg('h70,2*(WORD_COUNT+2),0); writeReg('h74,0,0); writeReg('h64,1,0);
    ownerPresent=3;
    repeat(9) begin @(negedge clock); data=data+11; addr=addr+1; wen=1; tick(); end
    capture();
    check(bankReads==3*WORD_COUNT,"exact bank read coverage");
    check(stalls>20 && functionalEdges>60,"active work and backpressure exercised");
    $display("GENERATED_NETWORK_PASS checks=%0d captures=%0d bank_reads=%0d stalls=%0d functional_edges=%0d",checks,captures,bankReads,stalls,functionalEdges);
    $finish;
  end
  initial begin #250000; $fatal(1,"network timeout"); end
endmodule
