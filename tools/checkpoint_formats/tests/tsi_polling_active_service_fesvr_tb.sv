module tsi_polling_active_service_fesvr_tb;
  import "DPI-C" function int tsi_active_service(input string source, destination);
  import "DPI-C" function void tsi_active_service_exit(input int code);
  string source, destination;
  integer result;
  initial begin
    if (!$value$plusargs("source=%s",source) || !$value$plusargs("destination=%s",destination))
      $fatal(1,"missing active service arguments");
    result=tsi_active_service(source,destination);
    if (result) tsi_active_service_exit(result);
    $finish;
  end
endmodule
