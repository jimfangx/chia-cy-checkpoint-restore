`timescale 1ns/1ps
module heartbeat_checkpoint_tb;
  import "DPI-C" function int heartbeat_init(input string directory, input int restore, input int cut, input int mode);
  import "DPI-C" function int heartbeat_step();
  import "DPI-C" function int heartbeat_negative(input string directory);
  import "DPI-C" function void heartbeat_failure();
  string directory;
  int restore_mode, cut, mode, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s", directory)) heartbeat_failure();
    if ($test$plusargs("negative")) begin
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
