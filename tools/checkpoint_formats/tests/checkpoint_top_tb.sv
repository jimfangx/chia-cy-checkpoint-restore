`timescale 1ns/1ps
// Only public FPGATop MMIO/AXI4 and fixture functional ports are used.
// The fixture has no CPU, FAME, host-memory or hardware-origin acceptance.
module checkpoint_top_tb;
  import "DPI-C" function void checkpoint_network_fail();
  `include "top_ports.svh"
  `include "top_bindings.svh"
  always #5 clock=~clock;
  integer checks=0,hostEdges=0,frozenEdges=0,dmaStalls=0,captures=0;
  integer frameFile=0,frameIndex=0,i,j,k,cut;
  reg [63:0] refCount=0,capturedCycle=0;
  reg [31:0] refMem[0:31];
  reg [31:0] snapshotMem[0:31];
  reg [511:0] frame,heldDMA;
  reg [31:0] value,produced;
  reg held=0,wasFrozen=0;
  task check(input bit condition,input string why);
    begin
      checks=checks+1;
      if(!condition) begin
        $display("TOP_FAIL %s target_cycle=%0d freeze=%0b frame=%0d",why,capturedCycle,fixtureFreeze,frameIndex);
        $fflush(); checkpoint_network_fail(); $fatal(1,"unreachable failure exit");
      end
    end
  endtask
  task tick; begin @(posedge clock); #1; end endtask
  always @(posedge clock) begin
    hostEdges=hostEdges+1;
    if(fixtureFreeze && !wasFrozen) begin
      capturedCycle=refCount;
      for(integer n=0;n<32;n=n+1) snapshotMem[n]=refMem[n];
    end
    if(!fixtureFreeze) begin
      refCount=fixtureReset?0:refCount+1;
      if(fixtureWen) refMem[fixtureAddr]=fixtureData;
    end
    if(!reset) begin
      if(fixtureFreeze) begin frozenEdges=frozenEdges+1; check(fixtureCount===capturedCycle,"common frozen cut"); end
      if(held) check(cpu_managed_axi4_r_valid && cpu_managed_axi4_r_bits_data===heldDMA,"AXI R stable under backpressure");
      held=cpu_managed_axi4_r_valid && !cpu_managed_axi4_r_ready;
      if(held) begin heldDMA=cpu_managed_axi4_r_bits_data; dmaStalls=dmaStalls+1; end
    end
    wasFrozen=fixtureFreeze;
    #1;
    if(!reset) begin
      check(fixtureCount===refCount,"independent functional counter");
      check(fixtureRam===refMem[fixtureAddr],"independent functional RAM");
    end
  end

  task writeReg(input [31:0] address,input [31:0] data,input [1:0] expected);
    begin
      // Send W first, then AW, through the real interconnect. No sideband MMIO.
      fork
        begin
          @(negedge clock); ctrl_w_bits_data=data; ctrl_w_valid=1;
          do begin @(posedge clock); end while(!ctrl_w_ready);
          @(negedge clock); ctrl_w_valid=0;
        end
        begin
          repeat(2) tick;
          @(negedge clock); ctrl_aw_bits_addr=address; ctrl_aw_valid=1;
          do begin @(posedge clock); end while(!ctrl_aw_ready);
          @(negedge clock); ctrl_aw_valid=0;
        end
      join
      repeat(3) tick;
      @(negedge clock); ctrl_b_ready=1;
      do begin @(posedge clock); end while(!ctrl_b_valid);
      check(ctrl_b_bits_resp===expected && ctrl_b_bits_id===12'd3,"MMIO write response/id");
      @(negedge clock); ctrl_b_ready=0;
    end
  endtask
  task readReg(input [31:0] address,output [31:0] data);
    begin
      @(negedge clock); ctrl_ar_bits_addr=address; ctrl_ar_valid=1;
      do begin @(posedge clock); end while(!ctrl_ar_ready);
      @(negedge clock); ctrl_ar_valid=0;
      repeat(2) tick;
      @(negedge clock); ctrl_r_ready=1;
      do begin @(posedge clock); end while(!ctrl_r_valid);
      check(ctrl_r_bits_resp===0 && ctrl_r_bits_last && ctrl_r_bits_id===12'd9,"MMIO read response/id");
      data=ctrl_r_bits_data;
      @(negedge clock); ctrl_r_ready=0;
    end
  endtask
  task dmaRead(input [63:0] address,output [511:0] data);
    begin
      @(negedge clock); cpu_managed_axi4_ar_bits_addr=address; cpu_managed_axi4_ar_valid=1;
      do begin @(posedge clock); end while(!cpu_managed_axi4_ar_ready);
      @(negedge clock); cpu_managed_axi4_ar_valid=0;
      // The real AXI buffer must hold a frame while the host stops accepting it.
      repeat(7) tick;
      @(negedge clock); cpu_managed_axi4_r_ready=1;
      do begin @(posedge clock); end while(!cpu_managed_axi4_r_valid);
      data=cpu_managed_axi4_r_bits_data;
      check(cpu_managed_axi4_r_bits_id===16'd21 && cpu_managed_axi4_r_bits_resp===0 &&
        cpu_managed_axi4_r_bits_last,"DMA read response/id/last");
      @(negedge clock); cpu_managed_axi4_r_ready=0;
    end
  endtask
  task acknowledgeDrain;
    begin
      readReg(CAPTURE_BASE+'h68,produced);
      readReg(CAPTURE_BASE+'h6c,value); check(value===0,"frame counter high half");
      writeReg(CAPTURE_BASE+'h70,produced,0);
      writeReg(CAPTURE_BASE+'h74,0,0);
      writeReg(CAPTURE_BASE+'h64,1,0);
      readReg(CAPTURE_BASE+'h60,value); check(value===0,"drain clears stream poison");
    end
  endtask
  task collectCapture(input integer index);
    begin
      frameFile=$fopen($sformatf("capture-%0d.frames",index),"wb");
      check(frameFile!=0,"open unpublished transport bytes");
      writeReg(CAPTURE_BASE,1,0);
      // Fill the actual two-frame FIFO and leave the host stalled. Capture
      // must stay frozen with a partial transfer, not drain target execution.
      repeat(180) tick;
      check(fixtureFreeze,"capture freeze survives full stream queue");
      readReg(STREAM_COUNT,value); check(value===2,"actual checkpoint FIFO full");
      readReg(CAPTURE_BASE+'h68,produced); check(produced < (index+1)*(WORD_COUNT+2),"transport backpressured before trailer");
      // Attempt target reset and writes during the accepting cut.
      @(negedge clock); fixtureReset=1; fixtureWen=1; fixtureAddr=7; fixtureData='hdeadbeef;
      for(frameIndex=0;frameIndex<WORD_COUNT+2;frameIndex=frameIndex+1) begin
        dmaRead(CAPTURE_DMA,frame);
        check(frame[63:0]===64'h3154504b434d5346 && frame[79:64]===16'd1,"frame ABI");
        check(frame[159:96]===capturedCycle,"exact target cut label");
        if(frameIndex==0) check(frame[95:80]===1 && frame[255:224]===ENTRY_COUNT &&
          frame[511:256]===MANIFEST_HASH,"manifest-bound header");
        else if(frameIndex<=WORD_COUNT) begin
          check(frame[95:80]===2 && frame[223:160]===frameIndex-1,"ordered data frame");
          k=wordEntries[frameIndex-1]; j=wordAddresses[frameIndex-1];
          check(frame[255:224]===k && frame[287:256]===j && frame[303:288]===widths[k] &&
            frame[311:304]===banks[k] && frame[327:312]===slots[k],"entry/address/width/selectors");
          check(frame[399:336]===(kinds[k]==0?{32'd0,snapshotMem[j]}:capturedCycle),"functional-input state oracle");
        end else check(frame[95:80]===3 && frame[223:160]===WORD_COUNT,"complete trailer");
        for(i=0;i<64;i=i+1) $fwrite(frameFile,"%c",frame[i*8+:8]);
      end
      $fclose(frameFile); frameFile=0;
      readReg(CAPTURE_BASE+4,value); check(value[3:0]===4'd10,"ready awaiting atomic publication");
      check(fixtureFreeze && fixtureCount===capturedCycle,"publication retains exact frozen state");
      // Existing bridge stream zero is independently readable while frozen.
      dmaRead(0,frame); check(frame===512'ha55ac33c,"existing stream retains allocation/data");
      @(negedge clock); fixtureReset=0; fixtureWen=0;
      $display("TOP_CAPTURE index=%0d target_cycle=%0d words=%0d",index,capturedCycle,WORD_COUNT);
      writeReg(CAPTURE_BASE,2,0);
      repeat(3) tick; check(!fixtureFreeze && fixtureCount>capturedCycle,"explicit release resumes functional edges");
      acknowledgeDrain;
      captures=captures+1;
    end
  endtask
  initial begin
    $dumpfile("top.vcd"); $dumpvars(0,checkpoint_top_tb);
    reset=1; fixtureReset=1; fixtureHostPresent=1; fixtureHostFrozen=1;
    fixtureCorrupt=$test$plusargs("corrupt-state");
    ctrl_aw_bits_size=2; ctrl_aw_bits_burst=1; ctrl_aw_bits_id=3;
    ctrl_w_bits_last=1; ctrl_w_bits_strb=15;
    ctrl_ar_bits_size=2; ctrl_ar_bits_burst=1; ctrl_ar_bits_id=9;
    cpu_managed_axi4_ar_bits_size=6; cpu_managed_axi4_ar_bits_burst=1; cpu_managed_axi4_ar_bits_id=21;
    repeat(5) tick;
    @(negedge clock); reset=0; fixtureReset=0;
    for(cut=0;cut<32;cut=cut+1) begin
      @(negedge clock); fixtureWen=1; fixtureAddr=cut; fixtureData='h10203040+17*cut;
      tick;
    end
    @(negedge clock); fixtureWen=0;
    repeat(12) tick;
    readReg(CAPTURE_BASE+'h20,value); check(value===ENTRY_COUNT,"global MMIO entry count");
    readReg(CAPTURE_BASE+'h40,value); check(value===MANIFEST_HASH[31:0],"global MMIO manifest hash");
    // Missing real host owner rejects before any frames enter the shared FIFO.
    @(negedge clock); fixtureHostPresent=0;
    writeReg(CAPTURE_BASE,1,0); repeat(20) tick;
    readReg(CAPTURE_BASE+8,value); check(value!=0 && fixtureFreeze,"missing owner rejected frozen");
    readReg(STREAM_COUNT,value); check(value===0,"missing owner publishes no DMA");
    writeReg(CAPTURE_BASE,4,0); repeat(4) tick;
    check(!fixtureFreeze,"abort missing-owner capture");
    acknowledgeDrain;
    @(negedge clock); fixtureHostPresent=1;
    collectCapture(0);
    for(cut=0;cut<9;cut=cut+1) begin
      @(negedge clock); fixtureWen=1; fixtureAddr=cut*3; fixtureData='h88776600+cut;
      tick;
    end
    @(negedge clock); fixtureWen=0;
    collectCapture(1);
    // Abort while the actual FIFO is full. Empty polling is not drain proof.
    writeReg(CAPTURE_BASE,1,0); repeat(180) tick;
    readReg(STREAM_COUNT,value); check(value===2,"partial capture filled actual FIFO");
    writeReg(CAPTURE_BASE,4,0); repeat(4) tick;
    readReg(CAPTURE_BASE+'h60,value); check(value[0],"abort poisons shared stream");
    writeReg(CAPTURE_BASE,1,2);
    writeReg(CAPTURE_BASE+'h64,1,2);
    dmaRead(CAPTURE_DMA,frame); dmaRead(CAPTURE_DMA,frame);
    acknowledgeDrain;
    collectCapture(2);
    check(captures===3 && dmaStalls>20 && frozenEdges>500,"complete integration stress");
    $display("CHECKPOINT_TOP_PASS checks=%0d captures=%0d dma_stalls=%0d frozen_edges=%0d",checks,captures,dmaStalls,frozenEdges);
    $finish;
  end
  initial begin #1000000; check(0,"timeout"); end
endmodule

// A channel sink for this standalone fixture. This is not generated CPU state.
module TargetBox(input hostClock,input hostReset,input clock_valid,input clock_bits,output clock_ready);
  assign clock_ready=1'b1;
endmodule
