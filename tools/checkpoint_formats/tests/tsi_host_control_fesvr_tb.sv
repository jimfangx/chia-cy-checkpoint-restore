module tsi_host_control_fesvr_tb;
  import "DPI-C" function int tsi_host_fesvr(input string elf, out_dir, count);
  import "DPI-C" function void tsi_host_fesvr_exit(input int status);
  string elf, out_dir, count;
  integer status;
  initial begin
    if (!$value$plusargs("elf=%s",elf) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("count=%s",count)) $fatal(1,"missing arguments");
    status=tsi_host_fesvr(elf,out_dir,count);
    if (status) tsi_host_fesvr_exit(status);
    $finish;
  end
endmodule
