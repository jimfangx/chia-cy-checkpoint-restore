module tsi_bridge_actual_checkpoint_tb;
  import "DPI-C" function int tsi_bridge_actual(input string image, out_dir, elf, chunk);
  import "DPI-C" function void tsi_bridge_actual_exit(input int status);
  string image, out_dir, elf, chunk;
  integer status;
  initial begin
    if (!$value$plusargs("image=%s",image) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("elf=%s",elf) || !$value$plusargs("chunk=%s",chunk)) $fatal(1,"missing argument");
    status=tsi_bridge_actual(image,out_dir,elf,chunk);
    if(status) tsi_bridge_actual_exit(status);
    $finish;
  end
endmodule
