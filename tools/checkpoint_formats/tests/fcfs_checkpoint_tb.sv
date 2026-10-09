module fcfs_checkpoint_tb;
  import "DPI-C" function int fcfs_checkpoint_init(input string source, input string outdir,
      input int restore_mode, input int cut, input int scenario);
  import "DPI-C" function int fcfs_checkpoint_run();
  import "DPI-C" function int fcfs_checkpoint_negative();
  bit clock = 0;
  always #5 clock = ~clock;
  string source, outdir;
  int restore_mode, cut, scenario, rc;
  initial begin
    if ($test$plusargs("negative")) begin
      rc = fcfs_checkpoint_negative();
    end else begin
      if (!$value$plusargs("source=%s", source) || !$value$plusargs("outdir=%s", outdir) ||
          !$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut) ||
          !$value$plusargs("scenario=%d", scenario)) $fatal(1, "missing options");
      rc = fcfs_checkpoint_init(source, outdir, restore_mode, cut, scenario);
      @(posedge clock);
      $display("FIXTURE_EDGE");
      rc = fcfs_checkpoint_run();
    end
    if (rc) $fatal(1, "simulation component failed");
    $finish;
  end
endmodule
