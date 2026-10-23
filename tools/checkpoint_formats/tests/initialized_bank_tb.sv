`timescale 1ns/1ps
// No simulator deposits or private state reads. Both RAMs start from their
// independently specified power-up images and are checked via public ports.
module initialized_bank_tb;
  reg clock=0,referenceClock=0;
  reg [2:0] addr=0;
  reg [8:0] data=0;
  reg wen=0;
  wire [8:0] left,right,originalLeft,originalRight;
  reg ckpt_freeze=1,ckpt_reset=1,ckpt_req_valid=0,ckpt_resp_ready=0;
  reg [7:0] ckpt_bank=0;
  reg [15:0] ckpt_slot=0;
  reg [31:0] ckpt_address=0;
  wire ckpt_req_ready,ckpt_resp_valid,ckpt_resp_error,ckpt_match;
  wire [63:0] ckpt_resp_data,ckpt_data;
  InitializedStorage dut(.*);
  ReferenceInitializedStorage referenceDut(.clock(referenceClock),.addr(addr),.data(data),.wen(wen),
    .left(originalLeft),.right(originalRight));
  reg [8:0] memory[0:1][0:7];
  integer checks=0,reads=0,stalls=0,edges=0,captures=0,observations=0,i,j,logfile;
  `include "initialized_bindings.svh"
  task check(input bit ok,input string why);
    begin
      checks=checks+1;
      if(!ok) begin $display("INITIALIZED_BANK_FAIL %s edge=%0d",why,edges);$fatal(1);end
    end
  endtask
  task outputs;
    begin
      #1;
      check(left===memory[0][addr] && right===memory[1][addr],"independent power-up/write oracle");
      check({left,right}==={originalLeft,originalRight},"unchanged original circuit");
      observations=observations+1;
    end
  endtask
  task tick;
    begin
      if(!ckpt_freeze) begin
        edges=edges+1;
        if(wen) begin memory[0][addr]=data;memory[1][addr]=data^9'h1ff;end
      end
      #5;clock=1;if(!ckpt_freeze)referenceClock=1;
      outputs();clock=0;referenceClock=0;#4;
    end
  endtask
  task read_word(input [7:0] bank,input [15:0] slot,input [31:0] at,
                 input [63:0] expected,input bit error,input bit releaseFreeze);
    integer n;
    begin
      ckpt_bank=bank;ckpt_slot=slot;ckpt_address=at;ckpt_req_valid=1;ckpt_resp_ready=0;
      #1;check(ckpt_req_ready===1,"endpoint ready");tick();ckpt_req_valid=0;reads=reads+1;
      for(n=0;n<4;n=n+1)begin
        if(releaseFreeze)begin ckpt_freeze=0;addr=addr+1;data=data+13;wen=1;end
        ckpt_bank=255;ckpt_slot=65535;ckpt_address=32'hffffffff;
        #1;
        check(ckpt_resp_valid===1 && ckpt_req_ready===0,"one response under backpressure");
        check(ckpt_resp_error===error && ckpt_resp_data===expected,"latched exact initialized word");
        tick();stalls=stalls+1;
      end
      ckpt_resp_ready=1;tick();ckpt_resp_ready=0;#1;
      check(ckpt_resp_valid===0 && ckpt_req_ready===1,"one response retirement");
    end
  endtask
  task capture;
    integer e,a,beforeEdge;
    begin
      ckpt_freeze=1;wen=1;data=511;beforeEdge=edges;
      for(e=0;e<ENTRY_COUNT;e=e+1)for(a=0;a<depths[e];a=a+1)begin
        addr=a;
        read_word(banks[e],slots[e],a,{55'b0,memory[kinds[e]][a]},0,0);
        $fdisplay(logfile,"WORD cut=%0d cycle=%0d entry=%0d address=%0d data=%0d",
          captures,edges,e,a,memory[kinds[e]][a]);
      end
      check(edges==beforeEdge,"capture never advances functional time");
      captures=captures+1;
    end
  endtask
  initial begin
    $dumpfile("initialized.vcd");$dumpvars(0,initialized_bank_tb);
    logfile=$fopen("captured-words.log","w");check(logfile!=0,"capture log");
    for(i=0;i<8;i=i+1)begin memory[0][i]=17+i*29;memory[1][i]=401-i*31;end
    tick();tick();ckpt_reset=0;
    for(i=0;i<8;i=i+1)begin addr=i;outputs();end
    check(edges==0,"read initialized bytes before first functional edge");capture();
    ckpt_freeze=0;wen=1;
    for(i=0;i<7;i=i+1)begin addr=i;data=31+i*19;tick();end
    capture();
    ckpt_freeze=0;
    for(i=0;i<37;i=i+1)begin addr=(i*5)%8;data=(i*41+3)%512;wen=(i%3)!=0;tick();end
    capture();
    ckpt_freeze=0;
    for(i=0;i<111;i=i+1)begin addr=(i*3)%8;data=(i*29+11)%512;wen=(i%4)!=0;tick();end
    capture();
    // Bad selectors, over-wide addresses and absent freeze cannot alias a RAM.
    read_word(255,65535,0,0,1,0);
    read_word(banks[0],slots[0],8,0,1,0);
    read_word(banks[0],slots[0],32'hffffffff,0,1,0);
    ckpt_freeze=0;wen=0;read_word(banks[0],slots[0],0,0,1,0);
    // An abort/release may resume writes while a complete response is stalled.
    ckpt_freeze=1;
    read_word(banks[0],slots[0],3,{55'b0,memory[kinds[0]][3]},0,1);
    ckpt_freeze=1;wen=0;
    for(i=0;i<8;i=i+1)begin addr=i;outputs();end
    $fclose(logfile);
    $display("INITIALIZED_BANK_PASS checks=%0d reads=%0d stalls=%0d functional_edges=%0d captures=%0d observations=%0d",
      checks,reads,stalls,edges,captures,observations);
    $finish;
  end
  initial begin #100000;$fatal(1,"initialized endpoint timeout");end
endmodule
