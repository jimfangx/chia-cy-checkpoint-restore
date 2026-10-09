`timescale 1ns/1ps
module fased_checkpoint_tb;
  import "DPI-C" function int fased_init(input string reference_dir, input int restore, input int cut, input int scenario);
  import "DPI-C" function int fased_step();
  import "DPI-C" function int fased_negative();
  string reference_dir;
  int restore_mode, cut, scenario, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if ($test$plusargs("negative")) begin
      if (fased_negative()) $fatal(1,"negative checks failed");
      $finish;
    end else begin
      if (!$value$plusargs("reference=%s",reference_dir) || !$value$plusargs("restore=%d",restore_mode) ||
          !$value$plusargs("cut=%d",cut) || !$value$plusargs("scenario=%d",scenario)) $fatal(1,"missing arguments");
      if (fased_init(reference_dir,restore_mode,cut,scenario)) $fatal(1,"restore failed before first edge");
      do begin
        @(posedge clock); result = fased_step();
        if (result < 0) $fatal(1,"FASED operation failed");
      end while (!result);
      $display("PASS: FASED host component continuation");
      $finish;
    end
  end
endmodule
