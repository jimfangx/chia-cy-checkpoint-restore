module tsi_host_execution_fesvr_tb;
  import "DPI-C" function int tsi_outer_fesvr(input string mode, elf, terminal, metadata, source, plan, destination);
  import "DPI-C" function void tsi_outer_fesvr_exit(input int code);
  string mode, elf, terminal, metadata, source, plan, destination;
  integer result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("terminal=%s",terminal) || !$value$plusargs("metadata=%s",metadata) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing outer FESVR arguments");
    result=tsi_outer_fesvr(mode,elf,terminal,metadata,source,plan,destination);
    if (result) tsi_outer_fesvr_exit(result);
    $finish;
  end
endmodule
