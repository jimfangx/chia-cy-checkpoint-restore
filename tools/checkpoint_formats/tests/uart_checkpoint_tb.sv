`timescale 1ns/1ps
module uart_checkpoint_tb;
  import "DPI-C" function int uart_init(input string directory, input int restore, input int cut);
  import "DPI-C" function int uart_step();
  import "DPI-C" function int uart_negative(input string directory);
  import "DPI-C" function void uart_failure();
  string directory;
  int restore_mode, cut, result;
  bit clock = 0;
  always #5 clock = ~clock;
  initial begin
    if (!$value$plusargs("outdir=%s", directory)) uart_failure();
    if ($test$plusargs("negative")) begin
      if (uart_negative(directory)) uart_failure();
    end else begin
      if (!$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut)) uart_failure();
      if (uart_init(directory, restore_mode, cut)) uart_failure();
      $display("UART_READBACK edges=0");
      do begin
        @(posedge clock);
        result = uart_step();
        if (result < 0) uart_failure();
      end while (!result);
      $display("PASS: fresh UART component continuation");
    end
    $finish;
  end
endmodule
