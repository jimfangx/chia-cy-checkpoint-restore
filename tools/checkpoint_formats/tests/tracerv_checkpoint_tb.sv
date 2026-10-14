`timescale 1ns/1ps
module tracerv_checkpoint_tb;
  import "DPI-C" function int tracerv_init(input string directory, input int restore, input int cut, input int mode, input int hart);
  import "DPI-C" function int tracerv_step();
  import "DPI-C" function int tracerv_negative(input string directory);
  import "DPI-C" function void tracerv_failure();
  string directory;
  int restore_mode, cut, mode, hart, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s", directory)) tracerv_failure();
    if ($test$plusargs("negative")) begin
      if (tracerv_negative(directory)) tracerv_failure();
    end else begin
      if (!$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut) ||
          !$value$plusargs("mode=%d", mode) || !$value$plusargs("hart=%d", hart)) tracerv_failure();
      if (tracerv_init(directory, restore_mode, cut, mode, hart)) tracerv_failure();
      $display("TRACERV_READBACK edges=0");
      do begin
        @(posedge clock);
        result = tracerv_step();
        if (result < 0) tracerv_failure();
      end while (!result);
      $display("PASS: fresh tracerv component continuation");
    end
    $finish;
  end
endmodule
