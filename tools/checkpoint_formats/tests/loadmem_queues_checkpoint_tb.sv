module loadmem_queues_checkpoint_tb;
  import "DPI-C" function int loadmem_queues_checkpoint(input string mode, out_dir, commands, expected, image, cut);
  import "DPI-C" function void loadmem_queues_exit(input int status);
  string mode, out_dir, commands, expected, image, cut;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("commands=%s",commands) || !$value$plusargs("expected=%s",expected) ||
        !$value$plusargs("image=%s",image) || !$value$plusargs("cut=%s",cut)) $fatal(1,"missing argument");
    status=loadmem_queues_checkpoint(mode,out_dir,commands,expected,image,cut);
    if (status) loadmem_queues_exit(status);
    $finish;
  end
endmodule
