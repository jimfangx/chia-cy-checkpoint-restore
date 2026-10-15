module tsi_htif_options_fesvr_tb;
  import "DPI-C" function int tsi_htif_options(input string option);
  import "DPI-C" function void tsi_htif_options_exit(input int code);
  string option;
  integer result;
  initial begin
    if (!$value$plusargs("option=%s",option)) $fatal(1,"missing HTIF option");
    result=tsi_htif_options(option);
    if(result) tsi_htif_options_exit(result);
    $finish;
  end
endmodule
