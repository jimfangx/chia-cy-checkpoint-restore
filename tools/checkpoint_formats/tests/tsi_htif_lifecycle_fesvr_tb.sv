module tsi_htif_lifecycle_fesvr_tb;
  import "DPI-C" function int tsi_htif_lifecycle(input string mode, source, destination, raw, flush);
  import "DPI-C" function void tsi_htif_lifecycle_status(input int status);
  string mode, source, destination, raw, flush;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("destination=%s",destination) || !$value$plusargs("raw=%s",raw) ||
        !$value$plusargs("flush=%s",flush)) $fatal(1,"missing argument");
    status=tsi_htif_lifecycle(mode,source,destination,raw,flush);
    if(status) tsi_htif_lifecycle_status(status);
    $finish;
  end
endmodule
