// Production timing component only; this clock is not a target-cycle boundary.
module host_timing_checkpoint_tb;
  import "DPI-C" function int host_timing_checkpoint_init(input string outdir,
      input int cut, input int mode, input longint unsigned maximum,
      input longint unsigned seed);
  import "DPI-C" function int host_timing_checkpoint_step(input int index);
  import "DPI-C" function int host_timing_checkpoint_finish();
  bit clock = 0;
  always #5 clock = ~clock;
  string outdir;
  int cut, mode, rc;
  longint unsigned maximum, seed;
  initial begin
    if (!$value$plusargs("outdir=%s", outdir) ||
        !$value$plusargs("cut=%d", cut) || !$value$plusargs("mode=%d", mode) ||
        !$value$plusargs("maximum=%d", maximum) || !$value$plusargs("seed=%d", seed))
      $fatal(1, "missing options");
    rc = host_timing_checkpoint_init(outdir, cut, mode, maximum, seed);
    if (rc) $fatal(1, "restore failed before first edge");
    if (mode == 2) begin
      $display("PASS: VCS host timing negative checks");
      $finish;
    end
    for (int i = mode == 1 ? cut : 0; i < 7200; i++) begin
      @(posedge clock);
      rc = host_timing_checkpoint_step(i);
      if (rc) $fatal(1, "host timing operation failed");
    end
    rc = host_timing_checkpoint_finish();
    if (rc) $fatal(1, "owner finish failed");
    $display("PASS: VCS host timing component continuation cut=%0d", cut);
    $finish;
  end
endmodule
