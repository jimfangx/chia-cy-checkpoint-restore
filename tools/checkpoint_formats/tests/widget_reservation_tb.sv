`timescale 1ns/1ps
// Deliberately unbound hardware: only MMIO/stream allocation and rejection are tested.
module widget_reservation_tb;
  import "DPI-C" function void checkpoint_network_fail();
  `include "top_ports.svh"
  `include "top_bindings.svh"
  always #5 clock=~clock;
  integer checks=0;
  reg [31:0] value;
  reg [511:0] frame;
  task tick; begin @(posedge clock);#1;end endtask
  task check(input bit ok,input string why);
    begin
      checks++;
      if(!ok) begin $display("RESERVATION_FAIL checks=%0d reason=%s",checks,why);$dumpflush;checkpoint_network_fail();$fatal(1,"unreachable");end
    end
  endtask
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
  initial begin
    $dumpfile("reservation.vcd");$dumpvars(0,widget_reservation_tb);
    reset=1;`RESERVED_PRESENT=0;`RESERVED_FROZEN=0;`RESERVED_ERROR=0;`RESERVED_CYCLE=25;
    ctrl_aw_bits_size=2;ctrl_aw_bits_burst=1;ctrl_aw_bits_id=3;
    ctrl_w_bits_strb=15;ctrl_w_bits_last=1;
    ctrl_ar_bits_size=2;ctrl_ar_bits_burst=1;ctrl_ar_bits_id=9;
    cpu_managed_axi4_ar_bits_size=6;cpu_managed_axi4_ar_bits_burst=1;cpu_managed_axi4_ar_bits_id=21;
    repeat(20) tick();@(negedge clock);reset=0;
    repeat(20) tick();
    readReg(CAPTURE_BASE+'h20,value);check(value==7,"reserved entry count visible through actual MMIO");
    for(integer i=0;i<8;i++) begin
      readReg(CAPTURE_BASE+'h40+4*i,value);check(value===32'hffffffff,"explicit unbound sentinel identity");
    end
    readReg(BASELINE_COUNT,value);check(value==2,"original stream still allocated and active");
    dmaRead(BASELINE_DMA,frame);check(frame===512'ha55ac33c,"original stream DMA payload");
    writeReg(CAPTURE_BASE,1,0);repeat(40) tick();
    readReg(CAPTURE_BASE+'h04,value);check(value[4] && !value[2],"missing owner fails before capture completes");
    readReg(CAPTURE_BASE+'h08,value);check(value!=0,"missing-owner error retained");
    readReg(STREAM_COUNT,value);check(value==0,"no checkpoint DMA frame from unresolved owners");
    repeat(8) begin tick();check(reservedFreeze,"failed cut cannot acknowledge release");end
    writeReg(CAPTURE_BASE,4,0);repeat(8) tick();check(reservedFreeze,"software release cannot escape failed cut");
    @(negedge clock);reset=1;repeat(20) tick();check(!reservedFreeze,"reset recovers reserved transport");
    @(negedge clock);reset=0;repeat(20) tick();
    readReg(CAPTURE_BASE+'h04,value);check(value==1,"post-reset idle status");
    readReg(STREAM_COUNT,value);check(value==0,"checkpoint stream remains empty");
    readReg(BASELINE_COUNT,value);check(value==2,"original stream recovers after shared reset");
    dmaRead(BASELINE_DMA,frame);check(frame===512'ha55ac33c,"baseline DMA survives reset recovery");
    $display("RESERVATION_VCS_PASS checks=%0d missing_owner_rejected=1 reset_recovered=1 baseline_stream=1",checks);$finish;
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
