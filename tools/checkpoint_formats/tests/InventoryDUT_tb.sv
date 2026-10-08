`timescale 1ns/1ps
module InventoryDUT_tb;
  reg clock = 0;
  reg reset = 1;
  reg [8:0] data = 0;
  reg [2:0] addr = 0;
  reg wen = 0;
  wire [8:0] count, array0, array1, array2, left, right, ram;
  wire [1:0] phase;
  InventoryDUT dut(.*);
  always #5 clock = ~clock;

  initial begin
    @(posedge clock); #1;
    if (count !== 0 || phase !== 0 || left !== 0 || right !== 0) $fatal(1, "reset failed");
    @(negedge clock); reset = 0;
    for (integer i = 0; i < 8; i = i + 1) begin
      data = 9'h100 + i;
      addr = i;
      wen = 1;
      @(posedge clock); #1;
      if (count !== i + 1 || phase !== (i + 1) % 3) $fatal(1, "register/FSM mismatch at %0d", i);
      if (array0 !== data || array1 !== data + 1 || array2 !== data + 2) $fatal(1, "register array mismatch");
      if (left !== data || right !== data + 1) $fatal(1, "same-module instances mismatch");
      @(negedge clock);
    end
    wen = 0;
    for (integer i = 0; i < 8; i = i + 1) begin
      addr = i;
      #1;
      if (ram !== 9'h100 + i) $fatal(1, "logical SRAM mismatch at %0d", i);
      @(negedge clock);
    end
    $display("PASS: clean pre-FAME RTL registers, FSM, register array, repeated instances, SRAM");
    $finish;
  end
  initial begin
    #1000;
    $fatal(1, "timeout");
  end
endmodule
