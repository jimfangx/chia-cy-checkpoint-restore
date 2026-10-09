`timescale 1ns/1ps
module widget_checkpoint_tb;
  import "DPI-C" function int widget_init(input string directory, input int restore, input int cut);
  import "DPI-C" function int widget_step();
  import "DPI-C" function int widget_negative(input string directory);
  string directory;
  int restore_mode, cut, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s", directory)) $fatal(1,"missing outdir");
    if ($test$plusargs("negative")) begin
      if (widget_negative(directory)) $fatal(1,"negative checks failed");
      $finish;
    end else begin
      if (!$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut))
        $fatal(1,"missing mode/cut");
      // Native owners are prevalidated/loaded before any fixture clock edge.
      if (widget_init(directory, restore_mode, cut)) $fatal(1,"restore rejected before first edge");
      do begin
        @(posedge clock);
        result = widget_step();
        if (result < 0) $fatal(1,"widget step failed");
      end while (!result);
      $display("PASS: widget component continuation");
      $finish;
    end
  end
endmodule
