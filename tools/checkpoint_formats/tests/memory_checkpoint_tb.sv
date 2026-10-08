// VCS clocks the actual C++ metasim memory owner. This isolates that owner;
// no generated FAME/FASED RTL state or full-runtime restart is claimed.
module memory_checkpoint_tb;
  import "DPI-C" function int mm_checkpoint_init(input string outdir,
      input int cut, input int beat, input int restore_mode);
  import "DPI-C" function int mm_checkpoint_step(input int cycle);
  import "DPI-C" function int mm_checkpoint_finish();
  bit clock = 0;
  always #5 clock = ~clock;
  string outdir;
  int cut, beat, restore_mode, rc;
  initial begin
    if (!$value$plusargs("outdir=%s", outdir) ||
        !$value$plusargs("cut=%d", cut) ||
        !$value$plusargs("beat=%d", beat) ||
        !$value$plusargs("restore=%d", restore_mode)) $fatal(1, "missing options");
    rc = mm_checkpoint_init(outdir, cut, beat, restore_mode);
    if (rc) $fatal(1, "restore failed before first edge");
    for (int c = restore_mode ? cut : 0; c < 42; c++) begin
      @(posedge clock);
      rc = mm_checkpoint_step(c);
      if (rc) $fatal(1, "owner tick failed");
    end
    rc = mm_checkpoint_finish();
    if (rc) $fatal(1, "owner finish failed");
    $display("PASS: VCS memory owner continuation cut=%0d beat=%0d", cut, beat);
    $finish;
  end
endmodule
