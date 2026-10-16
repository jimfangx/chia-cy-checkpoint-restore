module tsi_memif_read_fesvr_tb;
  import "DPI-C" function int tsi_memif_read_fesvr(input string mode, source, destination, flush);
  import "DPI-C" function void tsi_memif_read_fesvr_exit(input int status);
  string mode, source, destination, flush;
  integer status;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("destination=%s",destination) || !$value$plusargs("flush=%s",flush)) $fatal(1,"missing argument");
    status=tsi_memif_read_fesvr(mode,source,destination,flush);
    if (status) tsi_memif_read_fesvr_exit(status);
    $finish;
  end
endmodule
