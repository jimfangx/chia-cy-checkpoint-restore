module tsi_init_resume_tb;
  import "DPI-C" function int tsi_init_resume(input string mode, elf, image, plan, out_dir, flush, msip);
  import "DPI-C" function void tsi_init_resume_exit(input int status);
  string mode, elf, image, plan, out_dir, flush, msip;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("image=%s",image) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("out=%s",out_dir) || !$value$plusargs("flush=%s",flush) ||
        !$value$plusargs("msip=%s",msip)) $fatal(1,"missing argument");
    status=tsi_init_resume(mode,elf,image,plan,out_dir,flush,msip);
    if (status) tsi_init_resume_exit(status);
    $finish;
  end
endmodule
