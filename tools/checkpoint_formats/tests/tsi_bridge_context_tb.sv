module tsi_bridge_context_tb;
  import "DPI-C" function int tsi_bridge_context(input string mode, elf, terminal, metadata,
    source, plan, destination, image_path, build_path);
  import "DPI-C" function void tsi_context_group_exit(input int code);
  string mode, elf, terminal, metadata, source, plan, destination, image_path, build_path;
  bit clock = 0;
  integer edges = 0;
  always #1 clock = ~clock;
  always @(posedge clock) edges++;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("elf=%s",elf) ||
        !$value$plusargs("terminal=%s",terminal) || !$value$plusargs("metadata=%s",metadata) ||
        !$value$plusargs("source=%s",source) || !$value$plusargs("plan=%s",plan) ||
        !$value$plusargs("destination=%s",destination) || !$value$plusargs("image_path=%s",image_path) ||
        !$value$plusargs("build_path=%s",build_path)) $fatal(1,"missing context image arguments");
    if (tsi_bridge_context(mode,elf,terminal,metadata,source,plan,destination,image_path,build_path))
      tsi_context_group_exit(2);
    if (edges || $time) $fatal(1,"context image transfer advanced RTL");
    $display("BRIDGE_CONTEXT_VCS_ZERO_EDGES time=%0t edges=%0d", $time, edges);
    $finish;
  end
endmodule
