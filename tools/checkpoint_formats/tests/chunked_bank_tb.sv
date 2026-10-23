`timescale 1ns/1ps
// Generated storage -> real descriptor ROM -> production MMIO/DMA transport.
// Oracles depend only on initial image values and public functional inputs.
module chunked_bank_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0; always #5 clock=~clock;
  reg reset=1,functionalReset=1,wen=0;
  reg [16:0] addr=0;
  reg [128:0] data=0;
  wire freeze;
  wire storageFreeze=freeze || reset;
  reg referenceClock=0;
  wire [8:0] narrowOut,originalNarrow;
  wire [128:0] wideOut,originalWide;
  wire signed [64:0] signedOut,originalSigned;
  wire [127:0] exactOut,originalExact;
  wire [511:0] vectorOut,originalVector;
  wire bankValid,bankReady,responseValid,responseReady,responseError;
  wire [63:0] responseData;
  wire [7:0] bank,descriptorBank;
  wire [15:0] slot,descriptorSlot,descriptorWidth;
  wire [31:0] address,entry,descriptorDepth;
  wire descriptorValid;
  reg [63:0] targetCycle=0,capturedCycle=0;
  reg ownerPresent=1,wasFrozen=0,held=0,corruptState=0;
  reg mmio_valid=0,mmio_write=0;
  reg [7:0] mmio_address=0;
  reg [31:0] mmio_wdata=0;
  wire mmio_ready,mmio_response_valid,mmio_response_error;
  wire [31:0] mmio_rdata;
  wire dma_valid,dma_last,dma_abort;
  wire [511:0] dma_data;
  reg [511:0] heldFrame;
  integer hostEdges=0,checks=0,frames=0,captures=0,stalls=0,bankReads=0,observations=0;
  integer frameFile=0,byteIndex,wordEntry,wordAddress;
  `include "chunked_bindings.svh"
  wire dma_ready=(hostEdges%11==0);
  ChunkedStorage storage(.clock(clock),.reset(functionalReset),.addr(addr),.data(data),.wen(wen),
    .narrowOut(narrowOut),.wideOut(wideOut),.signedOut(signedOut),.exactOut(exactOut),.vectorOut(vectorOut),
    .ckpt_reset(reset),.ckpt_freeze(storageFreeze),.ckpt_req_valid(bankValid),.ckpt_req_ready(bankReady),
    .ckpt_bank(bank),.ckpt_slot(slot),.ckpt_address(address),
    .ckpt_resp_valid(responseValid),.ckpt_resp_ready(responseReady),.ckpt_resp_data(responseData),
    .ckpt_resp_error(responseError),.ckpt_match(),.ckpt_data());
  ReferenceChunkedStorage original(.clock(referenceClock),.reset(functionalReset),.addr(addr),.data(data),.wen(wen),
    .narrowOut(originalNarrow),.wideOut(originalWide),.signedOut(originalSigned),.exactOut(originalExact),.vectorOut(originalVector));
  CheckpointCaptureDescriptorROM rom(.clock(clock),.reset(reset),.io_entry(entry),.io_valid(descriptorValid),
    .io_bank(descriptorBank),.io_slot(descriptorSlot),.io_bitWidth(descriptorWidth),.io_depth(descriptorDepth));
  CheckpointCaptureTransport #(.OWNERS(1),.ENTRIES(ENTRY_COUNT),.MANIFEST_SHA256(MANIFEST_HASH)) transport(
    .clock(clock),.reset(reset),.target_cycle(targetCycle),.owner_present(ownerPresent),
    .owner_frozen(freeze),.owner_error(1'b0),.freeze(freeze),
    .mmio_valid(mmio_valid),.mmio_write(mmio_write),.mmio_ready(mmio_ready),
    .mmio_address(mmio_address),.mmio_wdata(mmio_wdata),.mmio_response_valid(mmio_response_valid),
    .mmio_response_ready(1'b1),.mmio_rdata(mmio_rdata),.mmio_response_error(mmio_response_error),
    .descriptor_entry(entry),.descriptor_valid(descriptorValid),.descriptor_bank(descriptorBank),
    .descriptor_slot(descriptorSlot),.descriptor_width(descriptorWidth),.descriptor_depth(descriptorDepth),
    .bank_request_valid(bankValid),.bank_request_ready(bankReady),.bank(bank),.slot(slot),.address(address),
    .bank_response_valid(responseValid),.bank_response_ready(responseReady),
    .bank_response_data(responseData ^ (corruptState ? 64'd1 : 64'd0)),.bank_response_error(responseError),
    .dma_valid(dma_valid),.dma_ready(dma_ready),.dma_data(dma_data),.dma_last(dma_last),.dma_abort(dma_abort));
  reg [8:0] deep[0:65536];
  reg [128:0] wide[0:4];
  reg [64:0] signedReg;
  reg [127:0] exactReg;
  reg [511:0] vectorReg;
  function automatic [63:0] oracle(input integer kind,input integer at);
    case(kind)
      0:oracle=deep[at];
      1:oracle=wide[at/3] >> (64*(at%3));
      2:oracle=signedReg >> (64*at);
      3:oracle=exactReg >> (64*at);
      4:oracle=vectorReg >> (64*at);
      default:oracle='x;
    endcase
  endfunction
  task check(input bit ok,input string why);
    begin
      checks=checks+1;
      if(!ok)begin
        $display("CHUNKED_BANK_FAIL %s cut=%0d cycle=%0d frame=%0d freeze=%0b",why,captures,capturedCycle,frames,freeze);
        $fflush();checkpoint_network_fail();$fatal(1,"checker failure");
      end
    end
  endtask
  always @(negedge clock)referenceClock=0;
  always @(posedge clock)begin
    // Pulse the reference only for an acknowledged functional edge. A
    // combinationally gated clock would create a spurious edge on cut release.
    if(!storageFreeze)referenceClock=1;
    hostEdges<=hostEdges+1;
    if(!storageFreeze)begin
      targetCycle<=targetCycle+1;
      signedReg=functionalReset?65'h1ffffffffffffffff:data[64:0];
      exactReg=functionalReset?0:data[127:0];
      vectorReg=functionalReset?0:{4{data[127:0]}};
      if(wen)begin
        if(addr<65537)deep[addr]=data[8:0];
        if(addr[2:0]<5)wide[addr[2:0]]=data;
      end
    end
    if(!reset)begin
      if(freeze && !wasFrozen)capturedCycle=targetCycle;
      if(freeze)check(targetCycle===capturedCycle,"no functional edge while frozen");
      if(bankValid && bankReady)bankReads=bankReads+1;
      if(held)check(dma_valid && dma_data===heldFrame,"stable DMA frame under backpressure");
      held=dma_valid && !dma_ready;
      if(held)begin heldFrame=dma_data;stalls=stalls+1;end
      if(dma_valid && dma_ready)begin
        check(frameFile!=0,"only an open unpublished capture receives frames");
        check(dma_data[159:96]===capturedCycle,"exact target cut");
        if(frames==0)check(dma_data[511:256]===MANIFEST_HASH && dma_data[95:80]===1,"bound header");
        else if(frames<=WORD_COUNT)begin
          wordEntry=dma_data[255:224];wordAddress=dma_data[287:256];
          check(wordEntry<ENTRY_COUNT && wordAddress<depths[wordEntry],"bounded physical address");
          check(dma_data[223:160]===frames-1 && dma_data[95:80]===2,"ordered ordinal");
          check(dma_data[303:288]===widths[wordEntry] && dma_data[311:304]===banks[wordEntry] &&
            dma_data[327:312]===slots[wordEntry],"physical descriptor metadata");
          check(dma_data[399:336]===oracle(kinds[wordEntry],wordAddress),"functional-input chunk oracle");
          check(!dma_last,"no premature final beat");
        end else check(frames==WORD_COUNT+1 && dma_last && dma_data[223:160]===WORD_COUNT,"unique trailer");
        for(byteIndex=0;byteIndex<64;byteIndex=byteIndex+1)$fwrite(frameFile,"%c",dma_data[byteIndex*8+:8]);
        frames=frames+1;
      end
    end
    wasFrozen=freeze;
  end
  always @(negedge clock)begin
    #1;
    if(!reset && targetCycle>0)begin
      check(narrowOut===deep[addr],"deep public output oracle");
      check(wideOut===wide[addr[2:0]],"wide public output oracle");
      check({signedOut,exactOut,vectorOut}==={signedReg,exactReg,vectorReg},"register public output oracle");
      check({narrowOut,wideOut,signedOut,exactOut,vectorOut}===
        {originalNarrow,originalWide,originalSigned,originalExact,originalVector},"unchanged original RTL");
      observations=observations+1;
    end
  end
  task tick;begin @(posedge clock);#1;end endtask
  task writeReg(input [7:0] at,input [31:0] value);
    begin
      @(negedge clock);mmio_address=at;mmio_wdata=value;mmio_write=1;mmio_valid=1;
      do begin @(posedge clock);end while(!mmio_ready);
      #1;check(mmio_response_valid && !mmio_response_error,"MMIO command acknowledged");
      @(negedge clock);mmio_valid=0;mmio_write=0;
    end
  endtask
  task capture;
    begin
      frames=0;frameFile=$fopen($sformatf("cut%0d.bin",captures),"wb");check(frameFile!=0,"capture file");
      writeReg(0,1);
      functionalReset=1;wen=1;data='1;addr=0;
      while(frames<WORD_COUNT+2)tick();
      check(freeze,"all words received before release");
      $fclose(frameFile);frameFile=0;
      $display("CHUNKED_CAPTURE cut=%0d target_cycle=%0d words=%0d",captures,capturedCycle,WORD_COUNT);
      // Clear reset/write while the original cut is still held.
      @(negedge clock);functionalReset=0;wen=0;
      writeReg(0,2);check(!freeze,"publication releases");captures=captures+1;
    end
  endtask
  integer i;
  initial begin
    corruptState=$test$plusargs("corrupt-state");
    $dumpfile("chunked.vcd");$dumpvars(0,chunked_bank_tb);
    for(i=0;i<65537;i=i+1)deep[i]=(i*37+11)&511;
    for(i=0;i<5;i=i+1)wide[i]={1'b1,64'(i+1),64'(17+i*29)};
    repeat(3)tick();@(negedge clock);reset=0;
    tick();capture();
    for(i=0;i<40;i=i+1)begin
      @(negedge clock);addr=(i%2==0)?65536:(i%5);data={1'b1,64'(i*97+13),64'(i*83+9)};wen=1;tick();
    end
    capture();
    for(i=0;i<95;i=i+1)begin
      @(negedge clock);addr=(i%3==0)?65536:(i%5);data={1'b0,64'(i*113+29),64'(i*53+19)};wen=(i%4!=0);tick();
    end
    capture();
    check(bankReads==3*WORD_COUNT && stalls>100000 && observations>100000,"complete deep/wide coverage with backpressure");
    $display("CHUNKED_BANK_PASS checks=%0d captures=%0d reads=%0d stalls=%0d observations=%0d",checks,captures,bankReads,stalls,observations);
    $finish;
  end
  initial begin #30000000;checkpoint_network_fail();$fatal(1,"chunked timeout");end
endmodule
