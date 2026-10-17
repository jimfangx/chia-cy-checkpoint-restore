module tsi_context_threads_fesvr_tb;
  import "DPI-C" function int tsi_context_threads(input string operation, fault, input int signal_number,
    input string elf, terminal, metadata, source, destination);
  import "DPI-C" function void tsi_context_group_exit(input int code);
  string operation, fault, elf, terminal, metadata, source, destination;
  integer signal_number, result;
  initial begin
    if (!$value$plusargs("operation=%s",operation) || !$value$plusargs("fault=%s",fault) ||
        !$value$plusargs("signal_number=%d",signal_number) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("terminal=%s",terminal) || !$value$plusargs("metadata=%s",metadata) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("destination=%s",destination))
      $fatal(1,"missing aggregate thread arguments");
    result = tsi_context_threads(operation,fault,signal_number,elf,terminal,metadata,source,destination);
    if (result) tsi_context_group_exit(result);
    $finish;
  end
endmodule
