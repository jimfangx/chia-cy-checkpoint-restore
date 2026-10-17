module driver_creator_reservation_tb;
  import "DPI-C" function int driver_creator_reservation();
  bit clock = 0;
  integer edges = 0;
  always #1 clock = ~clock;
  always @(posedge clock) edges++;
  initial begin
    if (driver_creator_reservation()) $fatal(1,"driver creator reservation failed");
    if (edges || $time) $fatal(1,"preparation advanced RTL");
    $display("DRIVER_CREATOR_ZERO_EDGES time=%0t edges=%0d",$time,edges);
    $finish;
  end
endmodule
