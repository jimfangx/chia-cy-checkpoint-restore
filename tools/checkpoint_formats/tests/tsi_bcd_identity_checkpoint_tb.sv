module tsi_bcd_identity_checkpoint_tb;
  import "DPI-C" function int tsi_bcd_identity_checkpoint(input string mode, out_dir, plan, expected, source, cut);
  import "DPI-C" function void tsi_bcd_identity_exit(input int status);
  string mode, out_dir, plan, expected, source, cut;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("plan=%s",plan) || !$value$plusargs("expected=%s",expected) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("cut=%s",cut)) $fatal(1,"missing argument");
    status=tsi_bcd_identity_checkpoint(mode,out_dir,plan,expected,source,cut);
    if (status) tsi_bcd_identity_exit(status);
    $finish;
  end
endmodule
