module tsi_bcd_checkpoint_tb;
  import "DPI-C" function int tsi_bcd(input string mode, source, image, destination, input int cut);
  import "DPI-C" function void tsi_bcd_exit(input int code);
  string mode, source, image, destination;
  int cut, result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("image=%s",image) || !$value$plusargs("destination=%s",destination) ||
        !$value$plusargs("cut=%d",cut)) $fatal(1,"missing BCD arguments");
    result=tsi_bcd(mode,source,image,destination,cut);
    if(result) tsi_bcd_exit(result);
    $finish;
  end
endmodule
