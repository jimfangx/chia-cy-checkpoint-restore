module tsi_host_execution_checkpoint_tb;
  import "DPI-C" function int tsi_host_execution(input string source, plan, destination);
  import "DPI-C" function void tsi_host_execution_exit(input int code);
  string source, plan, destination;
  integer result;
  initial begin
    if (!$value$plusargs("source=%s",source) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing outer arguments");
    result=tsi_host_execution(source,plan,destination);
    if (result) tsi_host_execution_exit(result);
    $finish;
  end
endmodule
