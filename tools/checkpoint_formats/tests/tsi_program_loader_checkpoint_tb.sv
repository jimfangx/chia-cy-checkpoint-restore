module tsi_program_loader_checkpoint_tb;
  import "DPI-C" function int tsi_program_loader(input string source, destination, phase);
  import "DPI-C" function void tsi_program_loader_exit(input int code);
  string source, destination, phase;
  integer result;
  initial begin
    if (!$value$plusargs("source=%s",source) || !$value$plusargs("destination=%s",destination) ||
        !$value$plusargs("phase=%s",phase)) $fatal(1,"missing loader arguments");
    result=tsi_program_loader(source,destination,phase);
    if (result) tsi_program_loader_exit(result);
    $finish;
  end
endmodule
