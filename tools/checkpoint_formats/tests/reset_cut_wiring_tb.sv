`timescale 1ns/1ps
module reset_cut_wiring_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=~clock;
  reg controller_reset=1, reset_in=1,freeze_request=0,reset_writer_present=1;
  reg [2:0] owner_present=7;
  wire [7:0] a,b,ra,rb;
  wire [63:0] count,ref_count,cut_cycle;
  wire mask,stopped,read_enable,failed,functional_reset;
  wire [1:0] captured_ce,reset_error;
  wire [2:0] physical_error;
  wire reference_clock;
  integer checks=0, cuts=0,stalls=0;
  string fault;
  bit corrupt;
  ResetCutWiringFixture dut(.clock(clock),.controller_reset(controller_reset),
    .reset_in(reset_in),.freeze_request(freeze_request),.reset_writer_present(reset_writer_present),
    .owner_present(owner_present),.a(a),.b(b),.count(count),.cut_cycle(cut_cycle),
    .clock_mask(mask),.stopped(stopped),.read_enable(read_enable),.failed(failed),
    .functional_reset(functional_reset),.captured_ce(captured_ce),.physical_error(physical_error),.reset_error(reset_error));
  BUFGCE reference_gate(.I(clock),.CE(!mask),.O(reference_clock));
  ResetRoutingReference reference(.clock(reference_clock),.reset(reset_in),.a(ra),.b(rb),.count(ref_count));
  task check(input bit okay,input string why);
    checks=checks+1;
    if(!okay)begin
      $display("RESET_ROUTING_DIVERGENCE target_cycle=%0d signal=%s acknowledged_edges=0",count,why);
      checkpoint_widget_failed(); #2; $finish;
    end
  endtask
  task outputs;
    check({a,b,count}==={ra,rb,ref_count},"functional_outputs");
    check(dut.execution.left.reset===(mask ? dut.cut.captured_reset : reset_in),"left.reset");
    check(dut.execution.right.reset===(mask ? dut.cut.captured_reset : reset_in),"right.reset");
    check(dut.execution.checkpoint_physical_root_gate.CE===!mask,"root.CE");
    check(dut.execution.left.gate.I===clock && dut.execution.right.gate.I===clock,"native.I");
  endtask
  task step;
    @(posedge clock);#1;outputs();
  endtask
  task capture;
    reg [79:0] saved;
    integer n;
    freeze_request=1;
    n=0;
    while(!read_enable && n<16)begin step();n=n+1;end
    check(read_enable && stopped && !failed,"cut_ready");
    check(cut_cycle===count,"target_cut");
    outputs();saved={a,b,count};cuts=cuts+1;
    $display("RESET_ROUTING_CUT target_cycle=%0d",count);
    if(corrupt && count==17)begin
      force dut.execution.left.reset=1;
      #1;outputs();
    end
    if(fault!="" && count==17)begin
      if(fault=="reset") reset_in=1;
      else if(fault=="writer")reset_writer_present=0;
      else if(fault=="owner")owner_present=6;
      else check(0,"unknown_fault");
      #1;check(!read_enable,"fault_read_revocation");
      repeat(4)begin step();check(mask && failed && {a,b,count}===saved,"fault_hold");end
      freeze_request=0;reset_in=0;reset_writer_present=1;owner_present=7;
      repeat(4)begin step();check(mask && failed && !read_enable && {a,b,count}===saved,"sticky_fault");end
      $display("RESET_ROUTING_REJECT fault=%s target_cycle=17 acknowledged_edges=0",fault);
      $finish;
    end
    repeat(8)begin step();check({a,b,count}===saved && read_enable,"collection_hold");stalls=stalls+1;end
    freeze_request=0;
    n=0;while(mask && n<16)begin step();n=n+1;end
    check(!mask && !failed,"release");
  endtask
  initial begin
    $dumpfile("reset-routing.vcd");$dumpvars(0,reset_cut_wiring_tb);
    corrupt=$test$plusargs("corrupt");if(!$value$plusargs("fault=%s",fault))fault="";
    #120; // Retain reset through the native vendor global-startup interval.
    repeat(4)begin @(posedge clock);#1;end
    controller_reset=0;reset_in=0;
    capture();
    while(count<17)step();capture();
    while(count<128)step();capture();
    while(count<256)step();capture();
    while(count<320)step();
    check(cuts==4 && stalls==32,"test_scope");
    $display("RESET_ROUTING_PASS checks=%0d cycles=320 cuts=4 stalls=32",checks);$finish;
  end
  initial begin #100000;check(0,"watchdog");end
endmodule
