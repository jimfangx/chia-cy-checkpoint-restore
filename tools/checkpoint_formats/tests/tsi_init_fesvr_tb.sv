module tsi_init_fesvr_tb;
  import "DPI-C" function int tsi_init_fesvr(input string elf, out_dir, flush, msip);
  import "DPI-C" function void tsi_init_fesvr_exit(input int status);
  string elf, out_dir, flush, msip;
  integer status;
  initial begin
    if (!$value$plusargs("elf=%s",elf) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("flush=%s",flush) || !$value$plusargs("msip=%s",msip)) $fatal(1,"missing argument");
    status=tsi_init_fesvr(elf,out_dir,flush,msip);
    if (status) tsi_init_fesvr_exit(status);
    $finish;
  end
endmodule
