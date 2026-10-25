`timescale 1ns/1ps
// Native banks through the real FPGATop control and CPU-managed AXI engine.
// Public functional ports provide the independent arithmetic/RAM oracle.
module native_checkpoint_top_tb;
  import "DPI-C" function void checkpoint_network_fail();
  `include "top_ports.svh"
  `include "top_bindings.svh"
  always #5 clock=~clock;
  reg [63:0] expected_cycle=0,saved_cycle=0;
  reg [64:0] expected_left=0,expected_right=0;
  reg [129:0] expected_read,memory[0:7];
  integer checks=0,cuts=0,words=0,frames=0,stalls=0,step=0,fd=0,i;
  bit armed=0,corrupt;
  reg held=0;
  reg [511:0] heldDMA,frame;
  reg [31:0] value,produced;
  string fault;
  `include "native-selectors.svh"
  `include "native-widget-manifest.svh"
  function automatic [129:0] pattern(input reg [63:0] t);
    pattern={2'(t%4),64'hfedcba9876543210 ^ (t*64'h10001),64'h123456789abcdef0 ^ (t*64'h12345)};
  endfunction
  always @* begin
    native_enable=native_reset || native_cycle<8 ? 3 : native_cycle[1:0];
    native_address=native_cycle[2:0];native_data=pattern(native_cycle);
    native_write=native_cycle<8 || native_cycle%3!=0;
  end
  task tick; begin @(posedge clock); #1; end endtask
  task check(input bit condition,input string why);
    begin
      checks++;
      if(!condition) begin
        $display("NATIVE_TOP_FAIL cycle=%0d checks=%0d frame=%0d frozen=%0b reason=%s",
          expected_cycle,checks,frames,native_freeze,why);
        $dumpflush;checkpoint_network_fail();$fatal(1,"unreachable failure exit");
      end
    end
  endtask
  always @(posedge clock) begin
    step++;
    if(!native_mask) begin
      if(native_reset) begin
        expected_cycle=0;
        if(native_enable[0]) expected_left=0;
        if(native_enable[1]) expected_right=0;
      end else begin
        expected_cycle++;
        if(native_enable[0]) expected_left++;
        if(native_enable[1]) expected_right++;
      end
      expected_read=memory[native_address];
      if(native_write) memory[native_address]=native_data;
    end
    if(!reset) begin
      if(held) check(cpu_managed_axi4_r_valid && cpu_managed_axi4_r_bits_data===heldDMA,"AXI R stable under backpressure");
      held=cpu_managed_axi4_r_valid && !cpu_managed_axi4_r_ready;
      if(held) begin heldDMA=cpu_managed_axi4_r_bits_data;stalls++;end
    end else held=0;
    #1;
    if(armed) begin
      check(native_cycle===expected_cycle && native_left_count===expected_left && native_right_count===expected_right,
        "independent functional counters");
      check(native_read_data===expected_read,"independent old-read RAM and pipeline");
      if(native_mask) check(dut.nativeCapture.network.checkpoint_physical_root_gate_O===0,"physical root clock stopped");
      if(native_read_enable && native_cycle_fault==0 && native_owner_present==3)
        check(native_captured_ce===native_enable && native_cut_cycle==native_cycle,"same-cut CE and cycle");
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
  task acknowledgeDrain;
    begin
      readReg(CAPTURE_BASE+'h68,produced);readReg(CAPTURE_BASE+'h6c,value);
      check(value===0,"frame counter high half");
      writeReg(CAPTURE_BASE+'h70,produced,0);writeReg(CAPTURE_BASE+'h74,0,0);
      writeReg(CAPTURE_BASE+'h64,1,0);readReg(CAPTURE_BASE+'h60,value);
      check(value===0,"accounted DMA drain clears poison");
    end
  endtask
  task capture(input integer requested);
    begin
      while(native_cycle<requested) tick();
      writeReg(CAPTURE_BASE,1,0);
      while(!native_read_enable) tick();
      saved_cycle=expected_cycle;
      check(native_cut_cycle==saved_cycle,"sampled target cut");
      if(fault!="" && cuts==1) begin
        @(negedge clock);
        if(fault=="cycle") native_cycle_fault=1;
        else if(fault=="missing") native_owner_present=1;
        else check(0,"unknown fault");
        #2;check(!native_read_enable,"fault withdraws bank permission");
        repeat(4) tick();check(native_failed && native_freeze,"sticky failed cut");
        writeReg(CAPTURE_BASE,4,0);
        repeat(8) begin tick();check(native_cycle==saved_cycle && native_freeze,"failed cut acknowledges no edges");end
        readReg(CAPTURE_BASE+'h60,value);check(value==1,"failed cut poisons stream");
        $display("NATIVE_TOP_REJECT fault=%s cycle=%0d acknowledged_edges=0",fault,native_cycle);
        $finish;
      end
      repeat(180) tick();
      readReg(STREAM_COUNT,value);check(value==2 && native_freeze,"real DMA queue backpressures frozen capture");
      fd=$fopen($sformatf("capture-%0d.hex",cuts),"w");check(fd!=0,"open frame evidence");
      words=0;
      for(frames=0;frames<36;frames++) begin
        dmaRead(CAPTURE_DMA,frame);
        check(native_read_enable && native_freeze,"DMA from acknowledged cut");
        check(frame[63:0]==64'h3154504b434d5346 && frame[159:96]==saved_cycle,"frame magic and target cut");
        if(frames==0) check(frame[95:80]==1 && frame[255:224]==7 && frame[511:256]==MANIFEST,"manifest header");
        else if(frames<35) begin
          reg [31:0] e,a;reg [63:0] expected;
          e=frame[255:224];a=frame[287:256];
          check(frame[95:80]==2 && frame[223:160]==words,"ordered data");
          check(e<7 && frame[311:304]==(e<5?0:255) && frame[327:312]==(e<5?e:e-5),"actual generated selectors");
          check(frame[303:288]==(e<5?native_width(e):1) && a==(e<5?words-native_offset(e):0),"width/address");
          expected=e<5?oracle(e,a):(native_captured_ce>>(e-5))&1;
          if(corrupt && cuts==0 && words==0) expected^=1;
          check(frame[399:336]===expected,"independent native bank and CE payload");
          words++;
        end else check(frame[95:80]==3 && frame[223:160]==34,"complete trailer");
        $fdisplay(fd,"%0128h",frame);
      end
      $fclose(fd);fd=0;
      readReg(CAPTURE_BASE+4,value);check(value==10 && native_freeze,"publication holds cut");
      dmaRead(0,frame);check(frame===512'ha55ac33c,"existing stream retains allocation/data");
      $display("NATIVE_TOP_CAPTURE index=%0d cut=%0d words=%0d",cuts,saved_cycle,words);
      writeReg(CAPTURE_BASE,2,0);
      while(native_stopped || native_freeze) tick();
      acknowledgeDrain;cuts++;
    end
  endtask
  initial begin
    $dumpfile("native-top.vcd");$dumpvars(0,native_checkpoint_top_tb);
    corrupt=$test$plusargs("corrupt");if(!$value$plusargs("fault=%s",fault)) fault="";
    reset=1;native_reset=1;native_owner_present=3;
    ctrl_aw_bits_size=2;ctrl_aw_bits_burst=1;ctrl_aw_bits_id=3;
    ctrl_w_bits_last=1;ctrl_w_bits_strb=15;
    ctrl_ar_bits_size=2;ctrl_ar_bits_burst=1;ctrl_ar_bits_id=9;
    cpu_managed_axi4_ar_bits_size=6;cpu_managed_axi4_ar_bits_burst=1;cpu_managed_axi4_ar_bits_id=21;
    repeat(20) tick();@(negedge clock);reset=0;native_reset=0;
    while(native_cycle<12) tick();armed=1;
    capture(0);capture(80);capture(180);capture(320);
    // Cancel an unpublished full DMA queue and reset every native/transport
    // endpoint together, including the real shared stream engine.
    writeReg(CAPTURE_BASE,1,0);repeat(180) tick();
    readReg(STREAM_COUNT,value);check(value==2,"unpublished capture queued");
    @(negedge clock);armed=0;reset=1;native_reset=1;
    repeat(20) tick();check(!native_freeze && !native_failed,"common controller/endpoint reset");
    @(negedge clock);reset=0;native_reset=0;
    while(native_cycle<12) tick();armed=1;
    readReg(STREAM_COUNT,value);check(value==0,"reset purges unpublished shared DMA frames");
    capture(17);while(native_cycle<200) tick();
    check(cuts==5 && stalls>100,"complete cuts and continuation");
    $display("NATIVE_TOP_PASS checks=%0d cuts=5 words=170 stalls=%0d recovered_cycle=%0d",checks,stalls,native_cycle);
    $finish;
  end
  initial begin #1000000;check(0,"watchdog timeout");end
endmodule
