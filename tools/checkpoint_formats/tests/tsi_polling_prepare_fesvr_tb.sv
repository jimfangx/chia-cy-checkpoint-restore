module tsi_polling_prepare_fesvr_tb;
  import "DPI-C" function int tsi_polling_prepare(input string mode, elf, terminal, metadata, source, plan, destination);
  import "DPI-C" function void tsi_polling_prepare_exit(input int code);
  string mode, elf, terminal, metadata, source, plan, destination;
  int result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("terminal=%s",terminal) || !$value$plusargs("metadata=%s",metadata) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing polling preparation arguments");
    result=tsi_polling_prepare(mode,elf,terminal,metadata,source,plan,destination);
    if (result) tsi_polling_prepare_exit(result);
    $finish;
  end
endmodule
