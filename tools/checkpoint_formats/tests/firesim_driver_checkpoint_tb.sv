`timescale 1ns/1ps
module firesim_driver_checkpoint_tb;
  import "DPI-C" function int firesim_driver_init(input string source, input string outdir,
      input int restore_mode, input int cut, input int mode);
  import "DPI-C" function int firesim_driver_step();
  import "DPI-C" function int firesim_driver_negative();
  import "DPI-C" function void firesim_driver_failure();
  string source, outdir;
  int restore_mode, cut, mode, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if ($test$plusargs("negative")) begin
      if (firesim_driver_negative()) firesim_driver_failure();
    end else begin
      if (!$value$plusargs("source=%s", source) || !$value$plusargs("outdir=%s", outdir) ||
          !$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut) ||
          !$value$plusargs("mode=%d", mode)) firesim_driver_failure();
      if (firesim_driver_init(source, outdir, restore_mode, cut, mode)) firesim_driver_failure();
      $display("FIRESIM_DRIVER_READBACK edges=0");
      do begin
        @(posedge clock);
        result = firesim_driver_step();
        if (result < 0) firesim_driver_failure();
      end while (!result);
      $display("PASS: fresh FireSim driver VCS component continuation");
    end
    $finish;
  end
endmodule
