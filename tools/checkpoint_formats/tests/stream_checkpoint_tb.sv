`timescale 1ns/1ps
module stream_checkpoint_tb;
  import "DPI-C" function int stream_init(input string directory, input int restore, input int cut, input int beat);
  import "DPI-C" function int stream_step();
  import "DPI-C" function int stream_negative(input int beat);
  string directory;
  int restore_mode, cut, beat, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s", directory) || !$value$plusargs("beat=%d", beat)) $fatal(1,"missing configuration");
    if ($test$plusargs("negative")) begin
      if (stream_negative(beat)) $fatal(1,"negative checks failed");
      $finish;
    end else begin
      if (!$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut)) $fatal(1,"missing mode/cut");
      if (stream_init(directory, restore_mode, cut, beat)) begin
        $display("REJECTED_BEFORE_FIRST_EDGE");
        $finish;
      end
      do begin
        @(posedge clock);
        $display("FIXTURE_EDGE");
        result = stream_step();
        if (result < 0) $fatal(1,"stream step failed");
      end while (!result);
      $display("PASS: stream component continuation");
      $finish;
    end
  end
endmodule
