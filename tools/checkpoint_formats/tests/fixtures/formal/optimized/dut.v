// Original pre-FAME DUT with genuinely unread, dynamically changing state.
// Every declaration remains in the independent semantic checkpoint inventory.
module StateMapDUT(
  input clock, input reset, input enable, input write,
  input [1:0] address, input [3:0] data,
  output [3:0] held_out, output [3:0] count_out, output [3:0] read_out
);
  reg [3:0] held;
  reg [3:0] count;
  reg [3:0] ram [0:3];
  reg [3:0] unused;
  always @(posedge clock) begin
    if (reset) begin
      held <= 0;
      count <= 0;
      unused <= 0;
    end else begin
      unused <= unused + data;
      if (enable) begin
        held <= data;
        count <= count + 1'b1;
      end
    end
    if (write) ram[address] <= data;
  end
  assign held_out = held;
  assign count_out = count;
  assign read_out = ram[address];
endmodule
