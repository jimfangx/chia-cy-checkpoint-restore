// Same physical SRAM interface with complemented writable state.
module CKSRAM(input CP, input WE, input [1:0] A, input [3:0] D, output [3:0] Q);
  reg [3:0] contents [0:3];
  reg [1:0] port_address;
  reg port_write;
  reg [3:0] port_data;
  reg [3:0] pipeline;
  always @(posedge CP) begin
    port_address <= ~A;
    port_write <= ~WE;
    port_data <= ~D;
    if (~port_write) contents[~port_address] <= port_data;
    pipeline <= contents[~port_address];
  end
  assign Q = ~pipeline;
endmodule
