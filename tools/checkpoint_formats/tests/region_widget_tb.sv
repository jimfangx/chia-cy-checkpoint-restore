`timescale 1ns/1ps
// Existing SimWrapper execution captured through real host NASTI and CPU DMA.
// Oracle values use arithmetic and a separate old-read RAM model; no state access.
module region_widget_tb;
  import "DPI-C" function void checkpoint_network_fail();
  `include "top_ports.svh"
  `include "top_bindings.svh"
  always #5 clock=~clock;
  always @* `RESERVEDCYCLE=`CYCLE;
  reg [63:0] expected_cycle=0,saved_cycle=0;
  reg [129:0] expected_read,memory[0:7],peer_read,peer_memory[0:7];
  integer checks=0,cuts=0,words=0,total_words=0,frames=0,stalls=0,fd=0;
  bit armed=0,missing_owner;
  reg held=0;
  reg [511:0] held_dma,frame;
  reg [31:0] value,produced;
  task tick; begin @(posedge clock); #2; end endtask
  task check(input bit condition,input string why);
    begin
      checks++;
      if(!condition) begin
        $display("REGION_WIDGET_FAIL cycle=%0d checks=%0d reason=%s",expected_cycle,checks,why);
        // Let VCD record the failing task's freshly assigned frame/selectors.
        // The defect is detected with the target frozen; this advances no target edge.
        #1;$dumpall;$dumpflush;
        // VCS completes its scheduled file flush in the following time slot.
        #0.001;checkpoint_network_fail();$fatal(1,"unreachable");
      end
    end
  endtask
  always @(posedge clock) begin
    if(!`MASK) begin
      // The writer always stores the old target cycle at its low three address bits.
      expected_read=memory[expected_cycle[2:0]];
      memory[expected_cycle[2:0]]={66'd0,expected_cycle};
      peer_read=peer_memory[expected_cycle[2:0]];
      peer_memory[expected_cycle[2:0]]={66'd0,expected_cycle ^ 64'h1234};
      if(reset) expected_cycle=0; else expected_cycle++;
    end
    if(!reset) begin
      if(held) check(cpu_managed_axi4_r_valid && cpu_managed_axi4_r_bits_data===held_dma,
        "actual AXI DMA response stable under host backpressure");
      held=cpu_managed_axi4_r_valid && !cpu_managed_axi4_r_ready;
      if(held) begin held_dma=cpu_managed_axi4_r_bits_data;stalls++;end
    end else held=0;
    #2;
    if(armed) begin
      check(`CYCLE===expected_cycle && `PEERCYCLE===expected_cycle,
        "original simulator cycle follows independent active/frozen clock arithmetic");
    end
  end
  task writeReg(input [31:0] address,input [31:0] data,input [1:0] expected);
    begin
      fork
        begin
          @(negedge clock);ctrl_w_bits_data=data;ctrl_w_valid=1;
          do begin @(posedge clock);end while(!ctrl_w_ready);
          @(negedge clock);ctrl_w_valid=0;
        end
        begin
          repeat(2) tick;
          @(negedge clock);ctrl_aw_bits_addr=address;ctrl_aw_valid=1;
          do begin @(posedge clock);end while(!ctrl_aw_ready);
          @(negedge clock);ctrl_aw_valid=0;
        end
      join
      repeat(3) tick;
      @(negedge clock);ctrl_b_ready=1;
      do begin @(posedge clock);end while(!ctrl_b_valid);
      check(ctrl_b_bits_resp===expected && ctrl_b_bits_id===12'd3,"MMIO write response/id");
      @(negedge clock);ctrl_b_ready=0;
    end
  endtask
  task readReg(input [31:0] address,output [31:0] data);
    begin
      @(negedge clock);ctrl_ar_bits_addr=address;ctrl_ar_valid=1;
      do begin @(posedge clock);end while(!ctrl_ar_ready);
      @(negedge clock);ctrl_ar_valid=0;
      repeat(2) tick;
      @(negedge clock);ctrl_r_ready=1;
      do begin @(posedge clock);end while(!ctrl_r_valid);
      check(ctrl_r_bits_resp===0 && ctrl_r_bits_last && ctrl_r_bits_id===12'd9,"MMIO read response/id");
      data=ctrl_r_bits_data;
      @(negedge clock);ctrl_r_ready=0;
    end
  endtask
  task dmaRead(input [63:0] address,output [511:0] data);
    begin
      @(negedge clock);cpu_managed_axi4_ar_bits_addr=address;cpu_managed_axi4_ar_valid=1;
      do begin @(posedge clock);end while(!cpu_managed_axi4_ar_ready);
      @(negedge clock);cpu_managed_axi4_ar_valid=0;
      repeat(7) tick;
      @(negedge clock);cpu_managed_axi4_r_ready=1;
      do begin @(posedge clock);end while(!cpu_managed_axi4_r_valid);
      data=cpu_managed_axi4_r_bits_data;
      check(cpu_managed_axi4_r_bits_id===16'd21 && cpu_managed_axi4_r_bits_resp===0 && cpu_managed_axi4_r_bits_last,
        "DMA read response/id/last");
      @(negedge clock);cpu_managed_axi4_r_ready=0;
    end
  endtask

  function automatic [63:0] oracle(input integer entry,input integer at);
    reg [129:0] full;
    begin
      case(entry_kind(entry))
        0,3,4: full={66'd0,saved_cycle};
        1: full=entry_region(entry)==0 ? expected_read : peer_read;
        2: full=entry_region(entry)==0 ? memory[at/3] : peer_memory[at/3];
        5: full=1;
        default: full='x;
      endcase
      if(entry_kind(entry)==0 || entry_kind(entry)==5) oracle=full[63:0];
      else if(entry_kind(entry)==3 || entry_kind(entry)==4) oracle=full>>(64*(at%2));
      else oracle=full>>(64*(at%3));
    end
  endfunction
  task acknowledgeDrain;
    begin
      readReg(CAPTURE_BASE+'h68,produced);readReg(CAPTURE_BASE+'h6c,value);
      check(value===0,"produced count high half");
      writeReg(CAPTURE_BASE+'h70,produced,0);writeReg(CAPTURE_BASE+'h74,0,0);
      writeReg(CAPTURE_BASE+'h64,1,0);readReg(CAPTURE_BASE+'h60,value);
      check(value===0,"real shared DMA drain accounted");
    end
  endtask
  task capture(input integer requested);
    begin
      while(expected_cycle<requested) tick();
      @(negedge clock);`RESERVEDFROZEN=0;
      writeReg(CAPTURE_BASE,1,0);
      while(!`MASK) tick();
      saved_cycle=expected_cycle;
      repeat(11) begin
        tick();check((`CYCLE==saved_cycle && `PEERCYCLE==saved_cycle) && `RESERVEDFREEZE,"physical execution stops while owner ack delayed");
        readReg(STREAM_COUNT,value);check(value==0,"no DMA before all owners acknowledge");
      end
      @(negedge clock);`RESERVEDFROZEN=3;
      repeat(180) tick();
      readReg(STREAM_COUNT,value);check(value==2 && `MASK && `RESERVEDFREEZE,"real queue backpressures active captured state");
      readReg(CAPTURE_BASE+'h10,value);check(value==saved_cycle,"capture label binds original network public cycle");
      fd=$fopen($sformatf("capture-%0d.hex",cuts),"w");check(fd!=0,"open complete frame evidence");
      words=0;
      for(frames=0;frames<FRAMES;frames++) begin
        dmaRead(CAPTURE_DMA,frame);
        check(`MASK && `RESERVEDFREEZE && (`CYCLE==saved_cycle && `PEERCYCLE==saved_cycle),"state remains frozen through actual DMA");
        check(frame[63:0]==64'h3154504b434d5346 && frame[79:64]==1 && frame[159:96]==saved_cycle,
          "captured frame magic/version/common target cut");
        if(frames==0) check(frame[95:80]==1 && frame[255:224]==ENTRIES && frame[511:256]===EXPECTED_MANIFEST,
          "captured header matches independently bound manifest");
        else if(frames<FRAMES-1) begin
          reg [31:0] e,a; reg [63:0] expected;
          e=frame[255:224];a=frame[287:256];
          check(e<ENTRIES && frame[95:80]==2 && frame[223:160]==words,"ordered state frame");
          check(frame[311:304]==entry_bank(e) && frame[327:312]==entry_slot(e) &&
            frame[303:288]==entry_width(e) && a==words-entry_offset(e) && a<entry_depth(e),
            "independently reconstructed descriptor and address");
          expected=oracle(e,a);
          if(frame[399:336]!==expected)
            $display("REGION_WIDGET_PAYLOAD_MISMATCH cut=%0d word=%0d entry=%0d address=%0d expected=%016h actual=%016h payload_byte=42",saved_cycle,words,e,a,expected,frame[399:336]);
          check(frame[399:336]===expected,"independent captured bank payload");
          words++;total_words++;
        end else check(frame[95:80]==3 && frame[223:160]==WORDS,"complete transfer trailer");
        $fdisplay(fd,"%0128h",frame);
      end
      $fclose(fd);fd=0;
      readReg(CAPTURE_BASE+4,value);check(value==10 && `RESERVEDFREEZE,"complete unpublished capture retains cut");
      dmaRead(BASELINE_DMA,frame);check(frame===512'ha55ac33c,"original baseline stream payload preserved");
      writeReg(CAPTURE_BASE,2,0);
      while(`RESERVEDFREEZE || `MASK) tick();
      acknowledgeDrain();cuts++;
    end
  endtask
  task commonReset;
    begin
      @(negedge clock);armed=0;reset=1;`RESERVEDFROZEN=0;
      repeat(20) tick();check(!`RESERVEDFREEZE && !`MASK,"common reset recovers physical/transport endpoints");
      @(negedge clock);reset=0;`RESERVEDPRESENT=3;
      while(expected_cycle<12) tick();armed=1;
      readReg(STREAM_COUNT,value);check(value==0,"reset discards unpublished shared DMA frames");
      readReg(BASELINE_COUNT,value);check(value==2,"original stream allocation survives reset");
      dmaRead(BASELINE_DMA,frame);check(frame===512'ha55ac33c,"original stream execution survives reset");
    end
  endtask
  initial begin
    $dumpfile("region-widget.vcd");$dumpvars(0,region_widget_tb);
    missing_owner=$test$plusargs("missing-owner");
    reset=1;`RESERVEDPRESENT=3;`RESERVEDFROZEN=0;`RESERVEDERROR=0;
    ctrl_aw_bits_size=2;ctrl_aw_bits_burst=1;ctrl_aw_bits_id=3;
    ctrl_w_bits_last=1;ctrl_w_bits_strb=15;
    ctrl_ar_bits_size=2;ctrl_ar_bits_burst=1;ctrl_ar_bits_id=9;
    cpu_managed_axi4_ar_bits_size=6;cpu_managed_axi4_ar_bits_burst=1;cpu_managed_axi4_ar_bits_id=21;
    commonReset();
    readReg(CAPTURE_BASE+'h20,value);check(value==ENTRIES,"actual registered entry count");
    for(integer i=0;i<8;i++) begin
      readReg(CAPTURE_BASE+'h40+4*i,value);check(value===EXPECTED_MANIFEST[32*i+:32],"MMIO manifest matches descriptor identity");
    end
    if(missing_owner) begin
      @(negedge clock);`RESERVEDPRESENT=1;`RESERVEDFROZEN=3;
      writeReg(CAPTURE_BASE,1,0);repeat(40) tick();
      readReg(CAPTURE_BASE+4,value);check(value[4] && !value[2],"missing owner rejects read permission");
      readReg(STREAM_COUNT,value);check(value==0,"missing owner publishes no DMA");
      saved_cycle=expected_cycle;
      writeReg(CAPTURE_BASE,4,0);
      repeat(8) begin tick();check(`RESERVEDFREEZE && expected_cycle==saved_cycle,"failed physical cut cannot release");end
      commonReset();
      $display("REGION_WIDGET_REJECT missing_owner=1 reset_recovered=1");$finish;
    end
    capture(0);capture(180);capture(320);
    // Abandon a queued unpublished capture using the actual common host reset.
    @(negedge clock);`RESERVEDFROZEN=3;
    writeReg(CAPTURE_BASE,1,0);repeat(180) tick();
    readReg(STREAM_COUNT,value);check(value==2,"unpublished capture fills real shared queue");
    commonReset();capture(17);
    repeat(40) tick();check(expected_cycle>17 && cuts==4 && total_words==4*WORDS && stalls>20,"active continuation after all cuts/reset");
    $display("REGION_WIDGET_PASS checks=%0d cuts=%0d words=%0d stalls=%0d",checks,cuts,total_words,stalls);$finish;
  end
  initial begin #1000000;check(0,"watchdog timeout");end
endmodule
