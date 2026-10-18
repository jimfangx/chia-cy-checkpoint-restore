module control_publication_tb;
  import "DPI-C" function int control_publication_test(input string mode, source, destination, input int unsigned scenario, cut);
  string mode, source, destination;
  int unsigned scenario, cut;
  bit clock = 0;
  int edges = 0;
  always #1 clock = ~clock;
  always @(posedge clock) edges++;
  initial begin
    if (!$value$plusargs("mode=%s", mode) || !$value$plusargs("source=%s", source) ||
        !$value$plusargs("destination=%s", destination) || !$value$plusargs("scenario=%d", scenario) ||
        !$value$plusargs("cut=%d", cut)) $fatal(1, "missing arguments");
    if (control_publication_test(mode, source, destination, scenario, cut)) $fatal(1, "publication failed");
    if ($time || edges) $fatal(1, "component advanced target edge");
    $display("CONTROL_VCS_ZERO_EDGES time=0 edges=0");
    $finish;
  end
endmodule
