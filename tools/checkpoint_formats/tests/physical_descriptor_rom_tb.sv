`timescale 1ns/1ps
// Exhaustive public-port ROM readback; no DUT hierarchy or state backdoors.
module physical_descriptor_rom_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=~clock;
  reg reset=1;
  reg [31:0] entry=0;
  wire valid;
  wire [7:0] bank;
  wire [15:0] slot, width;
  wire [31:0] depth;
  integer checks=0, i, phase;
  `include "descriptor_oracle.svh"
  PhysicalDescriptorROMProbe dut(.clock(clock),.reset(reset),.io_entry(entry),.io_valid(valid),
    .io_bank(bank),.io_slot(slot),.io_bitWidth(width),.io_depth(depth));
  task check(input [31:0] index);
    begin
      @(negedge clock); entry=index; #1;
      checks=checks+1;
      if ((index < ENTRY_COUNT && (!valid || bank !== banks[index] || slot !== slots[index] ||
           width !== widths[index] || depth !== depths[index])) ||
          (index >= ENTRY_COUNT && (valid || bank !== 0 || slot !== 0 || width !== 0 || depth !== 0))) begin
        $display("DESCRIPTOR_ROM_FAIL index=%0d checks=%0d",index,checks);
        checkpoint_widget_failed(); $finish;
      end
    end
  endtask
  initial begin
    $dumpfile("descriptor-rom.vcd"); $dumpvars(0,physical_descriptor_rom_tb);
    for(phase=0;phase<3;phase=phase+1) begin
      reset=(phase!=1);
      for(i=0;i<ENTRY_COUNT;i=i+1) begin check(i); check(32'hffffffff); end
      for(i=ENTRY_COUNT-1;i>=0;i=i-1) check(i);
      check(ENTRY_COUNT); check(ENTRY_COUNT+1); check(65535); check(65536);
      check(32'h80000000); check(32'hffff0000);
    end
    $display("DESCRIPTOR_ROM_PASS checks=%0d entries=%0d",checks,ENTRY_COUNT);
    $finish;
  end
endmodule
