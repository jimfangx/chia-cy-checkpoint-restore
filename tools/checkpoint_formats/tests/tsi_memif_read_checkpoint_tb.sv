module tsi_memif_read_checkpoint_tb;
  import "DPI-C" function int tsi_memif_read_checkpoint(input string mode, out_dir, plan, expected, image, queue, cut);
  import "DPI-C" function void tsi_memif_read_exit(input int status);
  string mode, out_dir, plan, expected, image, queue, cut;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("plan=%s",plan) || !$value$plusargs("expected=%s",expected) ||
        !$value$plusargs("image=%s",image) || !$value$plusargs("queue=%s",queue) ||
        !$value$plusargs("cut=%s",cut)) $fatal(1,"missing argument");
    status=tsi_memif_read_checkpoint(mode,out_dir,plan,expected,image,queue,cut);
    if (status) tsi_memif_read_exit(status);
    $finish;
  end
endmodule
