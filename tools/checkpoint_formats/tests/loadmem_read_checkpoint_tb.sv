module loadmem_read_checkpoint_tb;
  import "DPI-C" function int loadmem_read_checkpoint(
    input string mode, out_dir, bytes, image, queue, expected);
  string mode, out_dir, bytes, image, queue, expected;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s", mode) || !$value$plusargs("out=%s", out_dir))
      $fatal(1, "missing mode/out");
    if (!$value$plusargs("bytes=%s", bytes)) bytes="";
    if (!$value$plusargs("image=%s", image)) image="";
    if (!$value$plusargs("queue=%s", queue)) queue="";
    if (!$value$plusargs("expected=%s", expected)) expected="";
    // No simulation edge occurs before owner load or complete readback.
    status=loadmem_read_checkpoint(mode,out_dir,bytes,image,queue,expected);
    if(status) $fatal(1,"component returned %0d",status);
    $finish;
  end
endmodule
