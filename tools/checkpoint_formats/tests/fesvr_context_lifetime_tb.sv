module fesvr_context_lifetime_tb;
  import "DPI-C" function int fesvr_context_lifetime(input string mode);
  string mode;
  initial begin
    if (!$value$plusargs("mode=%s", mode)) mode = "checks";
    if (fesvr_context_lifetime(mode)) $fatal(1, "FESVR context lifetime failed");
    $finish;
  end
endmodule
