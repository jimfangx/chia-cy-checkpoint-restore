module tsi_terminal_checkpoint_tb;
  import "DPI-C" function int tsi_terminal(input string mode, source, images, destination, input int cut);
  import "DPI-C" function void tsi_terminal_exit(input int code);
  string mode, source, images, destination;
  int cut, result;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("images=%s",images) || !$value$plusargs("destination=%s",destination) ||
        !$value$plusargs("cut=%d",cut)) $fatal(1,"missing terminal arguments");
    result=tsi_terminal(mode,source,images,destination,cut);
    if(result) tsi_terminal_exit(result);
    $finish;
  end
endmodule
