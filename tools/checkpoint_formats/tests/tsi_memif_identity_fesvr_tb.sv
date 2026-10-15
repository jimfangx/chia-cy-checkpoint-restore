module tsi_memif_identity_fesvr_tb;
  import "DPI-C" function int tsi_memif_identity(input string mode, elf, input_path, plan, out_dir, flush, source_path);
  import "DPI-C" function void tsi_memif_identity_exit(input int status);
  string mode, elf, input_path, plan, out_dir, flush, source_path;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("input=%s",input_path) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("out=%s",out_dir) || !$value$plusargs("flush=%s",flush) ||
        !$value$plusargs("source=%s",source_path)) $fatal(1,"missing argument");
    status=tsi_memif_identity(mode,elf,input_path,plan,out_dir,flush,source_path);
    if (status) tsi_memif_identity_exit(status);
    $finish;
  end
endmodule
