module tsi_snapshot_handoff_tb;
  import "DPI-C" function int tsi_snapshot(input string elf, terminal, metadata, source, destination);
  import "DPI-C" function void tsi_context_group_exit(input int code);
  string elf, terminal, metadata, source, destination;
  bit clock = 0;
  integer edges = 0;
  always #1 clock = ~clock;
  always @(posedge clock) edges++;
  initial begin
    if (!$value$plusargs("elf=%s",elf) || !$value$plusargs("terminal=%s",terminal) ||
        !$value$plusargs("metadata=%s",metadata) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("destination=%s",destination)) $fatal(1,"missing snapshot arguments");
    if (tsi_snapshot(elf,terminal,metadata,source,destination)) tsi_context_group_exit(2);
    if (edges || $time) $fatal(1,"snapshot handoff advanced RTL");
    $display("SNAPSHOT_VCS_ZERO_EDGES time=%0t edges=%0d", $time, edges);
    $finish;
  end
endmodule
