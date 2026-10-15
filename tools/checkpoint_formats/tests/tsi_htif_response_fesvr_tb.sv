module tsi_htif_response_fesvr_tb;
  import "DPI-C" function int tsi_htif_response(input string mode, source, destination);
  import "DPI-C" function void tsi_htif_response_exit(input int code);
  string mode, source, destination;
  integer result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing response arguments");
    result=tsi_htif_response(mode,source,destination);
    if (result) tsi_htif_response_exit(result);
    $finish;
  end
endmodule
