// Actual C++ scheduler component only; no generated RTL/runtime cut claimed.
module scheduler_checkpoint_tb;
  import "DPI-C" function int scheduler_checkpoint_init(input string outdir,
      input int cut, input int restore_mode);
  import "DPI-C" function int scheduler_checkpoint_step(input int index);
  import "DPI-C" function int scheduler_checkpoint_finish();
  bit clock = 0;
  always #5 clock = ~clock;
  string outdir;
  int cut, restore_mode, rc;
  initial begin
    if (!$value$plusargs("outdir=%s", outdir) ||
        !$value$plusargs("cut=%d", cut) ||
        !$value$plusargs("restore=%d", restore_mode)) $fatal(1, "missing options");
    rc = scheduler_checkpoint_init(outdir, cut, restore_mode);
    if (rc) $fatal(1, "restore failed before first edge");
    for (int i = restore_mode ? cut : 0; i < 100; i++) begin
      @(posedge clock);
      rc = scheduler_checkpoint_step(i);
      if (rc) $fatal(1, "scheduler operation failed");
    end
    rc = scheduler_checkpoint_finish();
    if (rc) $fatal(1, "owner finish failed");
    $display("PASS: VCS scheduler component continuation cut=%0d", cut);
    $finish;
  end
endmodule
