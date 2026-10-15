module tsi_startup_metadata_fesvr_tb;
  import "DPI-C" function int tsi_startup_metadata(input string mode, source, image, destination);
  import "DPI-C" function void tsi_startup_metadata_exit(input int code);
  string mode, source, image, destination;
  integer result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("image=%s",image) || !$value$plusargs("destination=%s",destination)) $fatal(1,"missing metadata arguments");
    result=tsi_startup_metadata(mode,source,image,destination);
    if (result) tsi_startup_metadata_exit(result);
    $finish;
  end
endmodule
