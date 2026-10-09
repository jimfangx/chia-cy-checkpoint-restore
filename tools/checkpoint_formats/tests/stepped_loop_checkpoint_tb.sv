// Component driver/scheduler services; no generated RTL/runtime cut claimed.
module stepped_loop_checkpoint_tb;
  import "DPI-C" function int stepped_loop_checkpoint_init(input string outdir,
      input int cut, input int restore_mode, input int bridges, input int stop,
      input int horizon);
  import "DPI-C" function int stepped_loop_checkpoint_step(input int index);
  import "DPI-C" function int stepped_loop_checkpoint_finish();
  bit clock = 0;
  always #5 clock = ~clock;
  string outdir;
  int cut, restore_mode, bridges, stop, horizon, operations, rc;
  initial begin
    if (!$value$plusargs("outdir=%s", outdir) ||
        !$value$plusargs("cut=%d", cut) ||
        !$value$plusargs("restore=%d", restore_mode) ||
        !$value$plusargs("bridges=%d", bridges) ||
        !$value$plusargs("stop=%d", stop) ||
        !$value$plusargs("horizon=%d", horizon) ||
        !$value$plusargs("operations=%d", operations)) $fatal(1, "missing options");
    rc = stepped_loop_checkpoint_init(outdir, cut, restore_mode, bridges, stop, horizon);
    if (rc) $fatal(1, "restore failed before first edge");
    if (restore_mode == 2) begin
      $display("PASS: VCS stepped-loop negative checks");
      $finish;
    end
    for (int i = restore_mode ? cut : 0; i < operations; i++) begin
      @(posedge clock);
      rc = stepped_loop_checkpoint_step(i);
      if (rc) $fatal(1, "run-loop operation failed");
    end
    rc = stepped_loop_checkpoint_finish();
    if (rc) $fatal(1, "owner finish failed");
    $display("PASS: VCS stepped-loop component continuation cut=%0d", cut);
    $finish;
  end
endmodule
