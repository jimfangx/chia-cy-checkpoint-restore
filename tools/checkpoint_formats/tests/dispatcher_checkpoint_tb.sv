`timescale 1ns/1ps
module dispatcher_checkpoint_tb;
  import "DPI-C" function void dispatcher_init(input string src, input string dst,
    input int unsigned restore, input int unsigned cut, input int unsigned scenario,
    input int unsigned ticks);
  import "DPI-C" function int unsigned dispatcher_tick();
  import "DPI-C" function int unsigned dispatcher_pending();
  import "DPI-C" function int unsigned dispatcher_finished();
  import "DPI-C" function void dispatcher_settled();
  import "DPI-C" function void dispatcher_finish();
  string src, dst;
  int unsigned restore, cut, scenario, ticks;
  bit clock=0;
  always #1 clock=~clock;
  initial begin
    if (!$value$plusargs("source=%s",src) || !$value$plusargs("outdir=%s",dst) ||
        !$value$plusargs("restore=%d",restore) || !$value$plusargs("cut=%d",cut) ||
        !$value$plusargs("scenario=%d",scenario) || !$value$plusargs("ticks=%d",ticks)) $fatal;
    dispatcher_init(src,dst,restore,cut,scenario,ticks);
    if (dispatcher_finished()) begin dispatcher_finish(); $finish; end
  end
  always @(posedge clock) begin
    $display("FIXTURE_EDGE");
    if (dispatcher_tick()) begin dispatcher_finish(); $finish; end
    if (dispatcher_pending()) begin
      @(negedge clock); #0.001;
      dispatcher_settled();
      if (dispatcher_finished()) begin dispatcher_finish(); $finish; end
    end
  end
  initial begin #1000; $fatal; end
endmodule
