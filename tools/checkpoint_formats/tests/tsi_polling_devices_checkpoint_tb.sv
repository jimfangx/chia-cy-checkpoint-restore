module tsi_polling_devices_checkpoint_tb;
  import "DPI-C" function int tsi_polling_devices(input string mode, source, plan, destination, input int cut);
  import "DPI-C" function void tsi_polling_devices_exit(input int code);
  string mode, source, plan, destination;
  int cut, result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("plan=%s",plan) || !$value$plusargs("destination=%s",destination) ||
        !$value$plusargs("cut=%d",cut)) $fatal(1,"missing polling devices arguments");
    result=tsi_polling_devices(mode,source,plan,destination,cut);
    if (result) tsi_polling_devices_exit(result);
    $finish;
  end
endmodule
