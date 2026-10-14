module loadmem_transport_tb;
  import "DPI-C" function int loadmem_transport(input string elf, out_dir);
  string elf, out_dir;
  integer status;
  initial begin
    if (!$value$plusargs("elf=%s", elf) || !$value$plusargs("out=%s", out_dir)) $fatal(1,"missing elf/out");
    status=loadmem_transport(elf,out_dir);
    if(status) $fatal(1,"production loadmem transport returned %0d",status);
    $finish;
  end
endmodule
