`timescale 1ns/1ps
module native_checkpoint_widget_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=~clock;
  reg reset=1;
  reg awvalid=0,wvalid=0,arvalid=0,bready=0,rready=0;
  reg [31:0] awaddr=0,araddr=0,wdata=0;
  reg [7:0] awlen=0,arlen=0;
  reg [2:0] awsize=2,arsize=2;
  reg [3:0] awid=3,arid=9,strb=15;
  reg wlast=1;
  wire awready,wready,arready,bvalid,rvalid,rlast;
  wire [1:0] bresp,rresp;
  wire [3:0] bid,rid;
  wire [31:0] rdata;
  reg [1:0] owner_present=3;
  reg streamReady=0;
  wire streamValid,streamLast,streamAbort,clock_mask,physical_stopped,physical_read_enable,physical_failed,freeze;
  wire [511:0] streamData;
  wire [1:0] logical_ce,captured_ce;
  reg [1:0] ce_fault=0;
  reg [63:0] cycle_fault=0;
  wire [2:0] physical_error;
  wire [63:0] cycle,physical_cut_cycle;
  wire [64:0] left_count,right_count;
  wire [129:0] read_data;
  wire [1:0] enable=reset || cycle<8 ? 3 : cycle[1:0];
  wire [2:0] address=cycle[2:0];
  function automatic [129:0] pattern(input reg [63:0] t);
    pattern={2'(t%4),64'hfedcba9876543210 ^ (t*64'h10001),64'h123456789abcdef0 ^ (t*64'h12345)};
  endfunction
  wire [129:0] data=pattern(cycle);
  wire write=cycle<8 || cycle%3!=0;
  NativeCheckpointWidgetFixture dut(.*);
  reg [63:0] expected_cycle=0,saved_cycle=0;
  reg [64:0] expected_left=0,expected_right=0;
  reg [129:0] expected_read,memory[0:7];
  integer checks=0,cuts=0,words=0,frames=0,stalls=0,step=0,fd;
  bit armed=0,corrupt;
  reg stalled=0;
  reg [511:0] held;
  string fault,frames_path;
  `include "native-selectors.svh"
  `include "native-widget-manifest.svh"
  task tick; begin @(posedge clock); #1; end endtask
  task check(input bit cond, input string why); begin
    checks=checks+1; if (!cond) begin
      $display("NATIVE_WIDGET_DIVERGENCE cycle=%0d checks=%0d reason=%s",expected_cycle,checks,why);
      $dumpflush;
      checkpoint_widget_failed(); $finish;
    end
  end endtask
  task aw(input [31:0] addr); begin
    @(negedge clock); awaddr=addr; awvalid=1;
    do tick(); while (!dut.widget.adapter.haveAW);
    @(negedge clock); awvalid=0;
  end endtask
  task w(input [31:0] data, input bit last); begin
    @(negedge clock); wdata=data; wlast=last; wvalid=1;
    do begin @(posedge clock); end while (!wready);
    #1; @(negedge clock); wvalid=0;
  end endtask
  task ar(input [31:0] addr); begin
    @(negedge clock); araddr=addr; arvalid=1;
    do tick(); while (!dut.widget.adapter.haveAR);
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
  always @(posedge clock) begin
    step++;
    if(!clock_mask) begin
      if(reset) begin
        expected_cycle=0;
        if(enable[0]) expected_left=0;
        if(enable[1]) expected_right=0;
      end else begin
        expected_cycle++;
        if(enable[0]) expected_left++;
        if(enable[1]) expected_right++;
      end
      expected_read=memory[address];
      if(write) memory[address]=data;
    end
    #1;
    if(armed) begin
      check(cycle===expected_cycle && left_count===expected_left && right_count===expected_right,"independent functional counters");
      check(read_data===expected_read,"independent old-read RAM and pipeline");
      if(clock_mask) check(dut.access.network.checkpoint_physical_root_gate_O===0,"physical root clock stopped");
      if(physical_read_enable && fault=="")
        check(captured_ce===enable && physical_cut_cycle==cycle,"cut CE and target cycle");
    end
  end
  always @(posedge clock) begin
    if(reset) stalled<=0;
    else begin
      if(stalled && !streamAbort) check(streamValid && streamData===held,"stalled frame stability");
      stalled<=streamValid && !streamReady && !streamAbort;
      if(streamValid && !streamReady) begin stalls++; held<=streamData; end
      if(streamValid && streamReady) begin
        check(physical_read_enable && freeze && !streamAbort,"DMA only at acknowledged cut");
        check(streamData[63:0]==64'h3154504b434d5346 && streamData[159:96]==saved_cycle,"frame magic and target label");
        if(frames==0) check(streamData[95:80]==1 && streamData[255:224]==7 && streamData[511:256]==MANIFEST,"real descriptor manifest header");
        else if(streamData[95:80]==2) begin
          reg [31:0] e,a;
          reg [63:0] expected;
          e=streamData[255:224]; a=streamData[287:256];
          check(streamData[223:160]==words,"ordered transfer words");
          check(e<7 && streamData[311:304]==(e<5 ? 0 : 255) && streamData[327:312]==(e<5 ? e : e-5),"actual generated bank selectors");
          check(streamData[303:288]==(e<5 ? native_width(e) : 1),"actual generated transfer width");
          check(a==(e<5 ? words-native_offset(e) : 0),"logical word address");
          expected=e<5 ? oracle(e,a) : (captured_ce>>(e-5))&1;
          if(corrupt && cuts==0 && words==0) expected^=1;
          check(streamData[399:336]===expected,"independent native bank and CE payload");
          if(fd) $fdisplay(fd,"%0128h",streamData);
          words++;
        end else check(streamData[95:80]==3 && streamLast && words==34,"complete transfer trailer");
        if(fd && streamData[95:80]!=2) $fdisplay(fd,"%0128h",streamData);
        frames++;
      end
    end
  end
  task capture(input integer requested);
    while(cycle<requested) tick();
    @(negedge clock); streamReady=0;frames=0;words=0;
    command(1,0);
    while(!physical_read_enable) tick();
    saved_cycle=expected_cycle;
    check(physical_cut_cycle==saved_cycle,"sampled target cut");
    if(fault!="" && cuts==1) begin
      @(negedge clock);
      if(fault=="ce") ce_fault=1;
      else if(fault=="cycle") cycle_fault=1;
      else if(fault=="missing") owner_present=1;
      else check(0,"unknown failure injection");
      #2;check(!streamValid && !dut.bankValid && !physical_read_enable,"failure withdraws DMA and bank permissions");
      repeat(4) tick();check(physical_failed && freeze && streamAbort,"sticky cut fault");
      command(4,0);
      repeat(8) begin tick();check(cycle==saved_cycle && freeze,"failed cut acknowledges no edges");end
      readReg('h60,1);
      $display("NATIVE_WIDGET_REJECT fault=%s cycle=%0d acknowledged_edges=0",fault,cycle);
      $finish;
    end
    repeat(5) tick();
    while(frames<36) begin @(negedge clock);streamReady=step%4==0;tick();end
    @(negedge clock);streamReady=0;
    repeat(5) begin tick();check(cycle==saved_cycle && freeze,"publication stalls hold every functional owner");end
    readReg(4,10);readReg('h18,34);readReg('h20,7);
    command(2,0);
    while(physical_stopped || freeze) tick();
    cuts++;
    $display("NATIVE_WIDGET_CAPTURE requested=%0d cut=%0d words=%0d",requested,saved_cycle,words);
  endtask
  initial begin
    $dumpfile("native-widget.vcd");$dumpvars(0,native_checkpoint_widget_tb);
    corrupt=$test$plusargs("corrupt");
    if(!$value$plusargs("fault=%s",fault)) fault="";
    if($value$plusargs("frames=%s",frames_path)) begin fd=$fopen(frames_path,"w");check(fd!=0,"frame log opened");end
    repeat(20) tick();@(negedge clock);reset=0;
    while(cycle<12) tick();armed=1;
    // Cancel an unpublished stalled header, enforce invalidation and recovery.
    command(1,0);while(!streamValid) tick();
    command(4,0);while(freeze || physical_stopped) tick();
    readReg('h60,1);command(1,2);aw('h64);w(1,1);b(0);readReg('h60,0);
    capture(0);capture(80);capture(180);capture(320);
    while(cycle<440) tick();
    readReg('h68,144);readReg('h6c,0);
    check(cuts==4 && stalls>100,"complete cuts with sustained continuation and DMA stalls");
    // One reset reaches sampler/router/both endpoints/widget and functional owners.
    command(1,0);while(!streamValid) tick();
    @(negedge clock);armed=0;reset=1;#1;
    check(streamAbort && !streamValid && !dut.bankValid && !physical_read_enable,"reset instantly invalidates unpublished capture");
    repeat(5) tick();check(!freeze && !physical_failed && !dut.bank_response_valid,"common reset cancels router and endpoints");
    @(negedge clock);reset=0;while(cycle<12) tick();armed=1;
    capture(17);while(cycle<96) tick();
    $display("NATIVE_WIDGET_PASS checks=%0d cuts=%0d words=170 stalls=%0d recovered_cycle=%0d",checks,cuts,stalls,cycle);
    if(fd) $fclose(fd);$finish;
  end
  initial begin #500000;check(0,"watchdog timeout");end
endmodule
