`timescale 1ns/1ps
module blockdev_checkpoint_tb;
  import "DPI-C" function int blockdev_init(input string directory, input int restore, input int cut, input int compare);
  import "DPI-C" function int blockdev_step();
  import "DPI-C" function int blockdev_negative(input string directory);
  import "DPI-C" function void blockdev_failure();
  import "DPI-C" function int blockdev_publication_negative(input string directory);
  import "DPI-C" function void blockdev_publication_fatal(input string directory, input string mode);
  string fatal_mode;
  string directory;
  int restore_mode, cut, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s",directory)) blockdev_failure();
    if ($value$plusargs("publication-fatal=%s",fatal_mode)) begin
      blockdev_publication_fatal(directory,fatal_mode);blockdev_failure();
    end else if ($test$plusargs("publication-negative")) begin
      if (blockdev_publication_negative(directory)) blockdev_failure();
      if ($time != 0) blockdev_failure();
      $display("BLOCKDEV_PUBLICATION_ZERO_TIME_PASS");
    end else if ($test$plusargs("negative")) begin
      if (blockdev_negative(directory)) blockdev_failure();
    end else begin
      if (!$value$plusargs("restore=%d",restore_mode) || !$value$plusargs("cut=%d",cut)) blockdev_failure();
      if (blockdev_init(directory,restore_mode,cut,1)) blockdev_failure();
      $display("BLOCKDEV_READBACK edges=0");
      do begin
        @(posedge clock);
        result=blockdev_step();
        if (result<0) blockdev_failure();
      end while (!result);
      $display("PASS: blockdev component continuation");
    end
    $finish;
  end
endmodule
