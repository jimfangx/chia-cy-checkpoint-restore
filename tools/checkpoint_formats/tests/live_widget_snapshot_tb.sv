`timescale 1ns/1ps
module live_widget_snapshot_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=`SHADOW_BITS, WORDS=(BITS+63)/64;
  reg clock=0; always #5 clock=~clock;
  reg reset=1,access=0,write=0,cutValid=0;
  reg [BITS-1:0] live=0,expected;
  reg [63:0] cycle=0,label;
  reg [7:0] address=0;
  reg [31:0] data=0;
  wire [31:0] response;
  wire error;
  integer checks=0,captures=0,word_checks=0,epoch,word,bitnum;
  reg [63:0] expectedWord;
  CheckpointLiveWidgetSnapshot dut(.clock(clock),.reset(reset),.io_live(live),.io_cycle(cycle),
    .io_cutValid(cutValid),.io_access(access),.io_write(write),.io_address(address),.io_data(data),
    .io_response(response),.io_error(error));
  always @(posedge clock) begin
    cycle<=cycle+1;
    live<={live[BITS-2:0],live[BITS-1]^live[BITS-3]^live[5]^live[0]};
  end
  task check(input bit ok,input string why); begin
    checks++; if(!ok) begin
      $display("LIVE_SHADOW_DIVERGENCE bits=%0d epoch=%0d word=%0d reason=%s",BITS,epoch,word,why);
      checkpoint_widget_failed(); $finish;
    end
  end endtask
  task transaction(input bit wr,input [7:0] addr,input [31:0] value,input bit err);
    begin
      @(negedge clock);access=1;write=wr;address=addr;data=value;#1;
      check(error===err,"admission/error");
      @(posedge clock);#1;@(negedge clock);access=0;
    end
  endtask
  task read(input [7:0] addr,input [31:0] expectedResponse,input bit err); begin
    @(negedge clock);write=0;address=addr;data=0;#1;
    check(error===err && response===expectedResponse,"indexed read/error");
  end endtask
  task capture; begin
    @(negedge clock);access=1;write=1;address='h78;data=1;#1;
    check(!error,"certified capture");
    @(posedge clock);expected=live;label=cycle;captures++;#1;
    @(negedge clock);access=0;
  end endtask
  task allwords; begin
    read('h88,1,0);read('h8c,label[31:0],0);read('h90,label[63:32],0);read('h94,WORDS,0);
    for(word=0;word<WORDS;word++) begin
      transaction(1,'h7c,word,0);expectedWord=expected>>(word*64);
      read('h80,expectedWord[31:0],0);read('h84,expectedWord[63:32],0);word_checks++;
    end
    transaction(1,'h7c,WORDS,1);read('h7c,WORDS-1,0);
    transaction(1,'h7c,32'hffffffff,1);read('h7c,WORDS-1,0);
  end endtask
  initial begin
    $dumpfile("live-widget-snapshot.vcd");$dumpvars(0,live_widget_snapshot_tb);
    repeat(3) @(posedge clock);@(negedge clock);reset=0;
    read('h98,2,0);read('h9c,BITS,0);
    transaction(1,'h98,1,1);transaction(1,'h9c,BITS,1);
    transaction(1,'h78,1,1);read('h88,0,0);read('h80,0,1);
    transaction(1,'h78,2,1);transaction(1,'h78,3,1);transaction(1,'h88,1,1);
    for(epoch=0;epoch<64;epoch++) begin
      @(negedge clock);cutValid=1;
      for(bitnum=0;bitnum<BITS;bitnum++)live[bitnum]=$random;
      capture();allwords();
      @(negedge clock);cutValid=0;
      transaction(1,'h78,1,1);allwords(); // occupied history survives new source activity/fault
      transaction(1,'h78,epoch[0]?4:2,0);read('h88,0,0);read('h84,0,1);
    end
    @(negedge clock);cutValid=1;capture();
    @(negedge clock);reset=1;write=0;address='h88;#1;
    check(response==0 && error,"reset immediately hides old epoch");
    repeat(2) @(posedge clock);@(negedge clock);reset=0;read('h88,0,0);
    $display("LIVE_WIDGET_SNAPSHOT_PASS bits=%0d captures=%0d words=%0d checks=%0d",BITS,captures,word_checks,checks);
    $finish;
  end
  initial begin #3000000;check(0,"watchdog");end
endmodule
