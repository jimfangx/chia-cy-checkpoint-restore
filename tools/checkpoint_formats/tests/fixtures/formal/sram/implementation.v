// Explicit SRAM architecture supplied to synthesis; equivalence to dut.v is
// proved against the emitted netlist, never assumed from this source.
module StateMapDUT(
  input clock, input reset, input enable, input write,
  input [1:0] address, input [3:0] data,
  output [3:0] held_out, output [3:0] count_out, output [3:0] read_out
);
  reg [3:0] held;
  reg [3:0] count;
  always @(posedge clock) begin
    if (reset) begin held <= 0; count <= 0;
    end else if (enable) begin held <= data; count <= count + 1'b1; end
  end
  CKSRAM memory(.CP(clock),.WE(write),.A(address),.D(data),.Q(read_out));
  assign held_out = held;
  assign count_out = count;
endmodule
