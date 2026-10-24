`timescale 1ns/1ps
module host_pipeline_tb;
  import "DPI-C" function void checkpoint_network_fail();
  reg clock=0, otherClock=0, reset=1;
  wire [7:0] count, injected;
  HostPipeline dut(.*);
  integer checks=0, edges=0, i;
  reg [7:0] expectedCount=0, expectedInjected=19;
  task compare;
    begin
      checks=checks+1;
      if (count !== expectedCount || injected !== expectedInjected) begin
        $display("HOST_PIPELINE_FIRST_MISMATCH cycle=%0d count=%0d expected=%0d injected=%0d expected_injected=%0d",
                 edges,count,expectedCount,injected,expectedInjected);
        checkpoint_network_fail();
      end
    end
  endtask
  task tick;
    begin
      #5; clock=1;
      edges=edges+1;
      if (reset) begin expectedCount=0; expectedInjected=19; end
      else begin expectedCount=expectedCount+1; expectedInjected=expectedInjected+3; end
      #1; compare(); clock=0; #1;
      // Three non-host edges must not change either owner. The old compiler
      // path keeps the child on this clock and loses the injected owner.
      repeat (3) begin
        #1; otherClock=1; #1; compare(); otherClock=0;
      end
    end
  endtask
  initial begin
    $dumpfile("host-pipeline.vcd"); $dumpvars(0,host_pipeline_tb);
    tick(); reset=0;
    for (i=0;i<1024;i=i+1) begin
      reset=(i==511 || i==512); tick();
    end
    $display("HOST_PIPELINE_PASS checks=%0d edges=%0d",checks,edges);
    $finish;
  end
endmodule
