// Artificial zero-delay cells for synthesis/formal/restore tests only.
module CKBUF(input A, output Y);
assign Y = A;
endmodule
module CKINV(input A, output Y);
assign Y = ~A;
endmodule
module CKAND(input A, input B, output Y);
assign Y = A & B;
endmodule
module CKOR(input A, input B, output Y);
assign Y = A | B;
endmodule
module CKXOR(input A, input B, output Y);
assign Y = A ^ B;
endmodule
module CKMUX(input A, input B, input S, output Y);
assign Y = (~S & A) | (S & B);
endmodule
// Expose the complemented physical storage as QN; no hidden positive-polarity state.
module CKDFFN(input CP, input D, output QN);
reg state;
always @(posedge CP) state <= ~D;
assign QN = state;
endmodule
