module memory_publication_tb;
  import "DPI-C" function int memory_publication_test(input string mode, source, destination, input int unsigned cut, banks);
  string mode, source, destination;
  int unsigned cut, banks;
  bit clock = 0;
  int edges = 0;
  always #1 clock = ~clock;
  always @(posedge clock) edges++;
  initial begin
    if (!$value$plusargs("mode=%s", mode) || !$value$plusargs("source=%s", source) ||
        !$value$plusargs("destination=%s", destination) || !$value$plusargs("cut=%d", cut) ||
        !$value$plusargs("banks=%d", banks)) $fatal(1, "missing arguments");
    if (memory_publication_test(mode, source, destination, cut, banks)) $fatal(1, "memory publication failed");
    if ($time || edges) $fatal(1, "component advanced target edge");
    $display("MEMORY_VCS_ZERO_EDGES time=0 edges=0");
    $finish;
  end
endmodule
