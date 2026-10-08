// VCS clocks the actual metasim component owners; no generated RTL is present.
module mmio_checkpoint_tb;
  import "DPI-C" function int mmio_checkpoint_init(input string outdir,
      input int cut, input int beat, input int restore_mode);
  import "DPI-C" function int mmio_checkpoint_step(input int cycle);
  import "DPI-C" function int mmio_checkpoint_finish();
  bit clock = 0;
  always #5 clock = ~clock;
  string outdir;
  int cut, beat, restore_mode, rc;
  initial begin
    if (!$value$plusargs("outdir=%s", outdir) ||
        !$value$plusargs("cut=%d", cut) ||
        !$value$plusargs("beat=%d", beat) ||
        !$value$plusargs("restore=%d", restore_mode)) $fatal(1, "missing options");
    rc = mmio_checkpoint_init(outdir, cut, beat, restore_mode);
    if (rc) $fatal(1, "restore failed before first edge");
    for (int c = restore_mode ? cut : 0; c < 88; c++) begin
      @(posedge clock);
      rc = mmio_checkpoint_step(c);
      if (rc) $fatal(1, "component tick failed");
    end
    rc = mmio_checkpoint_finish();
    if (rc) $fatal(1, "component finish failed");
    $display("PASS: VCS MMIO/memory component continuation cut=%0d beat=%0d", cut, beat);
    $finish;
  end
endmodule
