module tsi_device_lifetime_tb;
  import "DPI-C" function int tsi_device_lifetime(input string source, destination);
  import "DPI-C" function void tsi_device_lifetime_exit(input int code);
  string source, destination;
  integer result;
  initial begin
    if (!$value$plusargs("source=%s", source) || !$value$plusargs("destination=%s", destination))
      $fatal(1, "missing device lifetime arguments");
    result = tsi_device_lifetime(source, destination);
    if (result) tsi_device_lifetime_exit(result);
    $finish;
  end
endmodule
