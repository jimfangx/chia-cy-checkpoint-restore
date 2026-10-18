module simulation_checkpoint_tb;
  import "DPI-C" function int simulation_checkpoint_init(input string source, input string outdir,
      input int restore_mode, input int cut, input int scenario);
  import "DPI-C" function int simulation_checkpoint_run();
  import "DPI-C" function int simulation_checkpoint_negative();
  import "DPI-C" function int simulation_publication_negative();
  import "DPI-C" function void simulation_publication_fatal(input string mode);
  import "DPI-C" function void simulation_checkpoint_failure();
  bit clock = 0;
  always #5 clock = ~clock;
  string source, outdir, fatal_mode;
  int restore_mode, cut, scenario, rc;
  initial begin
    if ($value$plusargs("publication-fatal=%s", fatal_mode)) begin
      simulation_publication_fatal(fatal_mode);
      simulation_checkpoint_failure();
    end else if ($test$plusargs("publication-negative")) begin
      rc = simulation_publication_negative();
      if ($time != 0) simulation_checkpoint_failure();
      $display("BASE_PUBLICATION_ZERO_TIME_PASS");
    end else if ($test$plusargs("negative")) begin
      rc = simulation_checkpoint_negative();
    end else begin
      if (!$value$plusargs("source=%s", source) || !$value$plusargs("outdir=%s", outdir) ||
          !$value$plusargs("restore=%d", restore_mode) || !$value$plusargs("cut=%d", cut) ||
          !$value$plusargs("scenario=%d", scenario)) $fatal(1, "missing options");
      rc = simulation_checkpoint_init(source, outdir, restore_mode, cut, scenario);
      @(posedge clock);
      $display("FIXTURE_EDGE");
      rc = simulation_checkpoint_run();
    end
    if (rc) $fatal(1, "simulation component failed");
    $finish;
  end
endmodule
