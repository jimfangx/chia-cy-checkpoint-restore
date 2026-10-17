module cpu_managed_io_checkpoint_tb;
  import "DPI-C" function int cpu_io_test(input string mode, source, destination, input int unsigned cut, beat);
  string mode, source, destination;
  int unsigned cut, beat;
  bit clock=0;
  int edges=0;
  always #1 clock=~clock;
  always @(posedge clock) edges++;
  initial begin
    if (!$value$plusargs("mode=%s",mode) || !$value$plusargs("source=%s",source) ||
        !$value$plusargs("destination=%s",destination) || !$value$plusargs("cut=%d",cut) ||
        !$value$plusargs("beat=%d",beat)) $fatal(1,"missing arguments");
    if(cpu_io_test(mode,source,destination,cut,beat)) $fatal(1,"CPU IO check failed");
    if($time || edges) $fatal(1,"component advanced target edge");
    $display("CPU_IO_VCS_ZERO_EDGES time=0 edges=0");
    $finish;
  end
endmodule
