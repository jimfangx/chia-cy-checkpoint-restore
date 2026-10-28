`timescale 1ns/1ps
module shell_state_access_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0;
  always #5 clock=~clock;
  reg reset=1, writeEn=0;
  reg [7:0] data=0;
  reg [1:0] address=0;
  wire [64:0] value;
  wire [7:0] cycle,memoryOut,childLive,siblingLive;
  reg freeze=0, endpoint_reset=1, request_valid=0, response_ready=0;
  reg [7:0] bank=0;
  reg [15:0] slot=0;
  reg [31:0] word_address=0;
  wire request_ready,response_valid,response_error;
  wire [63:0] response_data;
  // VCS VCD does not accept memory-word arguments to $dumpvars. Read-only
  // aliases retain every original byte in the full debug waveform.
  wire [7:0] debug_memory0=dut.enclosing.mem[0];
  wire [7:0] debug_memory1=dut.enclosing.mem[1];
  wire [7:0] debug_memory2=dut.enclosing.mem[2];
  wire [7:0] debug_memory3=dut.enclosing.mem[3];
  ShellTop dut(.clock(clock),.reset(reset),.data(data),.writeEn(writeEn),.address(address),
    .value(value),.cycle(cycle),.memoryOut(memoryOut),.childLive(childLive),.siblingLive(siblingLive),
    .checkpoint_shell_ckpt_clock(clock),.checkpoint_shell_ckpt_reset(endpoint_reset),
    .checkpoint_shell_ckpt_freeze(freeze),.checkpoint_shell_ckpt_req_valid(request_valid),
    .checkpoint_shell_ckpt_req_ready(request_ready),.checkpoint_shell_ckpt_bank(bank),
    .checkpoint_shell_ckpt_slot(slot),.checkpoint_shell_ckpt_address(word_address),
    .checkpoint_shell_ckpt_resp_valid(response_valid),.checkpoint_shell_ckpt_resp_ready(response_ready),
    .checkpoint_shell_ckpt_resp_data(response_data),.checkpoint_shell_ckpt_resp_error(response_error));
  reg [64:0] expected_value=0;
  reg [7:0] expected_cycle=0,expected_child=0,expected_read=0;
  reg [7:0] expected_memory[0:3];
  integer checks=0,reads=0,stalls=0,edges=0,cuts=0,cut_label=0;
  reg initialized=0;
  task check(input bit okay,input string why);
    begin
      checks=checks+1;
      if (!okay) begin
        $display("SHELL_DIVERGENCE cut=%0d bank=%0d slot=%0d word=%0d frozen=%0d edges=%0d signal=%s actual=%h expected=%h",
          cut_label,bank,slot,word_address,freeze,edges,why,response_data,expected_word);
        checkpoint_widget_failed();$finish;
      end
    end
  endtask
  always @(posedge clock) begin
    edges=edges+1;
    expected_child=reset ? 0 : expected_child+1;
    if (!freeze) begin
      expected_cycle=reset ? 0 : expected_cycle+1;
      expected_value=reset ? 0 : expected_value+65'd18446744073709551619;
      expected_read=expected_memory[address];
      if (writeEn) expected_memory[address]=data;
    end
  end
  always @(negedge clock) begin
    #1;
    if(edges>0) begin
    check(cycle===expected_cycle,"local cycle");
    check(value===expected_value,"wide local register");
    check(childLive===expected_child,"original child keeps executing");
    check(siblingLive===expected_child,"original sibling keeps executing");
    if (initialized) check(memoryOut===expected_read,"original synchronous read semantics");
    end
  end
  reg [63:0] expected_word=0;
  task readword(input integer b,input integer s,input integer a,input reg [63:0] expected,input bit error);
    integer i;
    begin
      @(negedge clock); #2;
      bank=b;slot=s;word_address=a;expected_word=expected;request_valid=1;
      check(request_ready,"empty endpoint ready");
      @(posedge clock); #2;
      request_valid=0;
      check(response_valid,"accepted response present");
      check(response_error===error,"response error");
      check(response_data===expected,"captured word");
      reads=reads+1;
      for(i=0;i<3+(reads%5);i=i+1) begin
        @(posedge clock); #2;
        check(response_valid && !request_ready,"backpressure holds response");
        check(response_data===expected && response_error===error,"stalled payload stable");
        stalls=stalls+1;
      end
      @(negedge clock); #2;response_ready=1;
      @(posedge clock); #2;response_ready=0;
      check(!response_valid && request_ready,"response consumed once");
    end
  endtask
  `include "shell_selectors.svh"
  task capture(input integer label);
    reg [7:0] child_before;
    begin
      @(negedge clock); #2;freeze=1;cut_label=label;child_before=childLive;
      allwords();
      readword(254,65535,0,0,1);
      check(childLive!==child_before,"bank access does not freeze child execution");
      // Functional reset remains held off locally during capture; children still see it.
      @(negedge clock); #2;reset=1;
      repeat(2) @(posedge clock);
      #2;allwords();
      @(negedge clock); #2;reset=0;freeze=0;
      repeat(3) @(posedge clock);
      cuts=cuts+1;
    end
  endtask
  integer i;
  initial begin
    $dumpfile("shell-state-access.vcd");$dumpvars(0,shell_state_access_tb);
    repeat(3) @(posedge clock);
    @(negedge clock); #2;reset=0;endpoint_reset=0;
    // Write every logical byte through the original functional memory port.
    for(i=0;i<4;i=i+1) begin
      @(negedge clock); #2;address=i;data=8'h31+i*17;writeEn=1;
      @(posedge clock); #2;
    end
    @(negedge clock); #2;writeEn=0;address=0;
    repeat(2) @(posedge clock); #2;initialized=1;
    capture(11);
    for(i=0;i<29;i=i+1) begin
      @(negedge clock); #2;address=i%4;data=i*7+13;writeEn=(i%3)!=0;
    end
    capture(41);
    for(i=0;i<37;i=i+1) begin
      @(negedge clock); #2;address=(i+1)%4;data=i*11+5;writeEn=1;
    end
    capture(81);
    for(i=0;i<55;i=i+1) begin
      @(negedge clock); #2;address=(i+2)%4;data=i*19+9;writeEn=(i%5)!=0;
    end
    capture(141);
    @(negedge clock); #2;writeEn=0;
    // An unfrozen read is an explicit failed request and never captures changing state.
    cut_label=142;readword(0,0,0,0,1);
    repeat(9) @(posedge clock);
    #2;check(cuts==4,"all four component cuts");
    $display("SHELL_STATE_ACCESS_PASS checks=%0d reads=%0d stalls=%0d edges=%0d cuts=%0d",checks,reads,stalls,edges,cuts);
    $finish;
  end
  initial begin #2000000;checkpoint_widget_failed();$fatal(1,"shell state watchdog");end
endmodule
