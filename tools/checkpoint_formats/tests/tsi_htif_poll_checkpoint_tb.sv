module tsi_htif_poll_checkpoint_tb;
  import "DPI-C" function int tsi_htif_poll(input string source, plan, destination);
  import "DPI-C" function void tsi_htif_poll_exit(input int code);
  string source, plan, destination;
  integer result;
  initial begin
    if (!$value$plusargs("source=%s",source) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing poll arguments");
    result=tsi_htif_poll(source,plan,destination);
    if (result) tsi_htif_poll_exit(result);
    $finish;
  end
endmodule
