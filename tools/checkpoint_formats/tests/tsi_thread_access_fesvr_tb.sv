module tsi_thread_access_fesvr_tb;
  import "DPI-C" function int tsi_thread_access(input string operation, elf, terminal, metadata, source, destination);
  import "DPI-C" function void tsi_context_group_exit(input int code);
  string operation, elf, terminal, metadata, source, destination;
  integer result;
  initial begin
    if (!$value$plusargs("operation=%s",operation) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("terminal=%s",terminal) || !$value$plusargs("metadata=%s",metadata) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("destination=%s",destination))
      $fatal(1,"missing thread access arguments");
    result = tsi_thread_access(operation,elf,terminal,metadata,source,destination);
    if (result) tsi_context_group_exit(result);
    $finish;
  end
endmodule
