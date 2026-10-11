// Original flat pre-FAME state, including an outstanding write and read pipeline.
module StateMapDUT(
  input clock, input reset, input enable, input write,
  input [1:0] address, input [3:0] data,
  output [3:0] held_out, output [3:0] count_out, output [3:0] read_out
);
  reg [3:0] held;
  reg [3:0] count;
  reg [3:0] ram [0:3];
  reg [1:0] addr_q;
  reg write_q;
  reg [3:0] data_q;
  reg [3:0] read_q;
  always @(posedge clock) begin
    if (reset) begin held <= 0; count <= 0;
    end else if (enable) begin held <= data; count <= count + 1'b1; end
    addr_q <= address;
    write_q <= write;
    data_q <= data;
    if (write_q) ram[addr_q] <= data_q;
    read_q <= ram[addr_q];
  end
  assign held_out = held;
  assign count_out = count;
  assign read_out = read_q;
endmodule
