module elfloader_policy_tb;
  import "DPI-C" function int elf_policy_check(input string path);
  import "DPI-C" function void elf_policy_exit(input int code);
  string path;
  int result;
  initial begin
    if (!$value$plusargs("source=%s",path)) $fatal(1,"missing source");
    result=elf_policy_check(path);
    if (result!=0) elf_policy_exit(result);
    $finish;
  end
endmodule
