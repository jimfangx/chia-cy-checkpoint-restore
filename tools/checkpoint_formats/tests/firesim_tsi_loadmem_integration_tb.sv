module firesim_tsi_loadmem_integration_tb;
  import "DPI-C" function int firesim_tsi_loadmem_integration(input string elf, out_dir);
  string elf, out_dir;
  integer status;
  initial begin
    if (!$value$plusargs("elf=%s", elf) || !$value$plusargs("out=%s", out_dir)) $fatal(1,"missing elf/out");
    status=firesim_tsi_loadmem_integration(elf,out_dir);
    if(status) $fatal(1,"actual FESVR integration returned %0d",status);
    $finish;
  end
endmodule
