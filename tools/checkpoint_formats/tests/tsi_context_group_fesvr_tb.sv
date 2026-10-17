module tsi_context_group_fesvr_tb;
  import "DPI-C" function int tsi_context_group(input string mode, elf, terminal, metadata, source, plan, destination);
  import "DPI-C" function void tsi_context_group_exit(input int code);
  string mode, elf, terminal, metadata, source, plan, destination;
  integer result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("terminal=%s",terminal) || !$value$plusargs("metadata=%s",metadata) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing context aggregate arguments");
    result=tsi_context_group(mode,elf,terminal,metadata,source,plan,destination);
    if (result) tsi_context_group_exit(result);
    $finish;
  end
endmodule
