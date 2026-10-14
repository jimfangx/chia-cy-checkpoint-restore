module tsi_host_control_checkpoint_tb;
  import "DPI-C" function int tsi_host_checkpoint(input string mode, out_dir, commands, expected, image, cut, variant);
  import "DPI-C" function void tsi_host_exit(input int status);
  string mode, out_dir, commands, expected, image, cut, variant;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("out=%s",out_dir) ||
        !$value$plusargs("commands=%s",commands) || !$value$plusargs("expected=%s",expected) ||
        !$value$plusargs("image=%s",image) || !$value$plusargs("cut=%s",cut) ||
        !$value$plusargs("variant=%s",variant)) $fatal(1,"missing argument");
    status=tsi_host_checkpoint(mode,out_dir,commands,expected,image,cut,variant);
    if (status) tsi_host_exit(status);
    $finish;
  end
endmodule
