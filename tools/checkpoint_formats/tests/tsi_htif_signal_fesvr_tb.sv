module tsi_htif_signal_fesvr_tb;
  import "DPI-C" function int tsi_htif_signal(input string mode, source, destination, scenario, detail);
  import "DPI-C" function void tsi_htif_signal_exit(input int status);
  string mode, source, destination, scenario, detail;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("destination=%s",destination) || !$value$plusargs("scenario=%s",scenario) ||
        !$value$plusargs("detail=%s",detail)) $fatal(1,"missing argument");
    status=tsi_htif_signal(mode,source,destination,scenario,detail);
    if(status) tsi_htif_signal_exit(status);
    $finish;
  end
endmodule
