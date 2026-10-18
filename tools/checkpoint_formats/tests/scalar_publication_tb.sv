module scalar_publication_tb;
  import "DPI-C" function int scalar_publication(input string mode, source, destination, input int cut);
  string mode, source, destination;
  int cut, result;
  initial begin
    if (!$value$plusargs("mode=%s", mode) || !$value$plusargs("source=%s", source) ||
        !$value$plusargs("destination=%s", destination) || !$value$plusargs("cut=%d", cut))
      $fatal(1, "missing scalar publication test arguments");
    result = scalar_publication(mode, source, destination, cut);
    if (result != 0 || $time != 0) $fatal(1, "scalar publication failed or advanced time");
    $display("SCALAR_VCS_ZERO_TIME_PASS");
    $finish;
  end
endmodule
