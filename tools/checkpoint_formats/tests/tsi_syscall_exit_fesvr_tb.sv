module tsi_syscall_exit_fesvr_tb;
  import "DPI-C" function int tsi_syscall_exit_fesvr(input string mode, out_dir, plan, expected, source, cut);
  import "DPI-C" function void tsi_syscall_exit_status(input int status);
  string mode, out_dir, plan, expected, source, cut;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("plan=%s",plan) || !$value$plusargs("expected=%s",expected) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("cut=%s",cut)) $fatal(1,"missing argument");
    status=tsi_syscall_exit_fesvr(mode,out_dir,plan,expected,source,cut);
    if (status) tsi_syscall_exit_status(status);
    $finish;
  end
endmodule
