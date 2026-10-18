`timescale 1ns/1ps
module heartbeat_checkpoint_tb;
  import "DPI-C" function int heartbeat_init(input string directory, input int restore, input int cut, input int mode);
  import "DPI-C" function int heartbeat_step();
  import "DPI-C" function int heartbeat_negative(input string directory);
  import "DPI-C" function void heartbeat_failure();
  import "DPI-C" function int heartbeat_publication_negative(input string directory);
  import "DPI-C" function void heartbeat_publication_fatal(input string directory, input string mode);
  string directory;
  string fatal_mode;
  int restore_mode, cut, mode, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s", directory)) heartbeat_failure();
    if ($value$plusargs("publication-fatal=%s", fatal_mode)) begin
      heartbeat_publication_fatal(directory, fatal_mode);
      heartbeat_failure();
    end else if ($test$plusargs("publication-negative")) begin
      if (heartbeat_publication_negative(directory)) heartbeat_failure();
      if ($time != 0) heartbeat_failure();
      $display("HEARTBEAT_PUBLICATION_ZERO_TIME_PASS");
    end else if ($test$plusargs("negative")) begin
      if (heartbeat_negative(directory)) heartbeat_failure();
    end else begin
      if (!$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut) ||
          !$value$plusargs("mode=%d", mode)) heartbeat_failure();
      if (heartbeat_init(directory, restore_mode, cut, mode)) heartbeat_failure();
      $display("HEARTBEAT_READBACK edges=0");
      do begin
        @(posedge clock);
        result = heartbeat_step();
        if (result < 0) heartbeat_failure();
      end while (!result);
      $display("PASS: fresh heartbeat component continuation");
    end
    $finish;
  end
endmodule
