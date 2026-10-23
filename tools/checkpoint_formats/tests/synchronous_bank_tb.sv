`timescale 1ns/1ps
// Public-input oracle and an independently emitted, unchanged original circuit.
module synchronous_bank_tb;
  reg clock=0, referenceClock=0;
  reg [2:0] addr=0;
  reg [8:0] data=0;
  reg ren=0,wen=0,wmode=0,mask=0;
  wire [8:0] oldMemOut,newMemOut,undefMemOut,rwOldOut,rwUndefOut;
  wire [8:0] originalOld,originalNew,originalUndef,originalRWOld,originalRWUndef;
  reg ckpt_freeze=0,ckpt_reset=1,ckpt_req_valid=0,ckpt_resp_ready=0;
  reg [7:0] ckpt_bank=0;
  reg [15:0] ckpt_slot=0;
  reg [31:0] ckpt_address=0;
  wire ckpt_req_ready,ckpt_resp_valid,ckpt_resp_error,ckpt_match;
  wire [63:0] ckpt_resp_data,ckpt_data;
  SyncStorage dut(.*);
  ReferenceStorage original(.clock(referenceClock),.addr(addr),.data(data),.ren(ren),
    .wen(wen),.wmode(wmode),.mask(mask),.oldMemOut(originalOld),.newMemOut(originalNew),
    .undefMemOut(originalUndef),.rwOldOut(originalRWOld),.rwUndefOut(originalRWUndef));
  reg [8:0] memory[0:4][0:7];
  reg [8:0] savedOld,savedRWOld,savedRWUndef;
  reg [2:0] savedNew,savedUndef;
  integer checks=0,reads=0,stalls=0,edges=0,captures=0,compared=0;
  reg initialized=0;
  `include "synchronous_bindings.svh"
  task check(input bit ok,input string why);
    begin
      checks=checks+1;
      if(!ok) begin $display("SYNCHRONOUS_BANK_FAIL %s edge=%0d",why,edges); $fatal(1); end
    end
  endtask
  task tick;
    integer m;
    begin
      if(!ckpt_freeze) begin
        edges=edges+1;
        if(ren) begin
          savedOld=memory[0][addr]; savedNew=addr; savedUndef=addr;
          // FIRRTL passthrough RW output samples old data even on write edges.
          savedRWOld=memory[3][addr]; savedRWUndef=memory[4][addr];
        end
        if(wen && mask) for(m=0;m<3;m=m+1) memory[m][addr]=data;
        if(ren && wmode && mask) for(m=3;m<5;m=m+1) memory[m][addr]=data;
      end
      #5; clock=1; if(!ckpt_freeze) referenceClock=1;
      #1;
      if(initialized) begin
        check({oldMemOut,newMemOut,undefMemOut,rwOldOut,rwUndefOut} ===
          {originalOld,originalNew,originalUndef,originalRWOld,originalRWUndef},
          $sformatf("unchanged original outputs got=%h/%h/%h/%h/%h expected=%h/%h/%h/%h/%h freeze=%b ren=%b wen=%b mode=%b mask=%b addr=%d data=%h",
          oldMemOut,newMemOut,undefMemOut,rwOldOut,rwUndefOut,
          originalOld,originalNew,originalUndef,originalRWOld,originalRWUndef,
          ckpt_freeze,ren,wen,wmode,mask,addr,data));
        check(oldMemOut===savedOld,"old reader data pipeline");
        check(newMemOut===memory[1][savedNew],"new reader address pipeline");
        check(undefMemOut===memory[2][savedUndef],"undefined reader address pipeline");
        check(rwOldOut===savedRWOld,"old RW data pipeline including writes");
        check(rwUndefOut===savedRWUndef,"undefined RW data pipeline including writes");
        compared=compared+1;
      end
      clock=0; referenceClock=0; #4;
    end
  endtask
  function automatic [63:0] oracle(input integer kind,input integer at);
    case(kind)
      0,1,2,3,4:oracle=memory[kind][at];
      5:oracle=savedOld;
      6:oracle=savedNew;
      7:oracle=savedUndef;
      8:oracle=savedRWOld;
      9:oracle=savedRWUndef;
      default:begin oracle=0;$fatal(1,"unknown owner");end
    endcase
  endfunction
  task read_word(input [7:0] bank,input [15:0] slot,input [31:0] at,
    input [63:0] expected,input bit error,input bit releaseFreeze);
    integer j;
    begin
      ckpt_bank=bank;ckpt_slot=slot;ckpt_address=at;ckpt_req_valid=1;ckpt_resp_ready=0;
      #1;check(ckpt_req_ready===1,"bank ready");tick();ckpt_req_valid=0;reads=reads+1;
      for(j=0;j<4;j=j+1) begin
        if(releaseFreeze) begin ckpt_freeze=0;data=data+13;addr=addr+1;ren=1;wen=1;wmode=1;mask=1;end
        ckpt_bank=255;ckpt_slot=65535;ckpt_address=32'hffffffff;
        #1;
        check(ckpt_resp_valid===1 && ckpt_req_ready===0,"one held response");
        check(ckpt_resp_error===error && ckpt_resp_data===expected,"complete saved bank word");
        tick();stalls=stalls+1;
      end
      ckpt_resp_ready=1;tick();ckpt_resp_ready=0;#1;
      check(ckpt_resp_valid===0 && ckpt_req_ready===1,"response retires once");
    end
  endtask
  task capture;
    integer i,a;
    begin
      // Freeze the accepting edge with every functional input attempting work.
      ckpt_freeze=1;ren=1;wen=1;wmode=1;mask=1;data=511;
      for(i=0;i<ENTRY_COUNT;i=i+1)
        for(a=0;a<depths[i];a=a+1)
          read_word(banks[i],slots[i],a,oracle(kinds[i],a),0,0);
      captures=captures+1;ckpt_freeze=0;
    end
  endtask
  integer i;
  initial begin
    $dumpfile("synchronous.vcd");$dumpvars(0,synchronous_bank_tb);
    tick();ckpt_reset=0;ren=1;wen=1;wmode=1;mask=1;
    for(i=0;i<8;i=i+1) begin addr=i;data=100+i;tick();end
    addr=3;wen=0;wmode=0;tick();initialized=1;tick();capture();
    // Independent read/write enables, masks, same-address collisions and holds.
    for(i=0;i<180;i=i+1) begin
      addr=(i*5+3)%8;data=(i*37+19)%512;ren=(i%4!=1);wen=(i%3!=0);
      wmode=(i%5!=2);mask=(i%7!=3);tick();
      if(i%23==7) capture();
    end
    ckpt_freeze=1;
    read_word(255,65535,0,0,1,0);
    read_word(banks[0],slots[0],depths[0],0,1,0);
    read_word(banks[0],slots[0],0,oracle(kinds[0],0),0,1);
    read_word(banks[0],slots[0],0,0,1,0);
    capture();
    $display("SYNCHRONOUS_BANK_PASS checks=%0d reads=%0d stalls=%0d functional_edges=%0d captures=%0d output_edges=%0d",checks,reads,stalls,edges,captures,compared);
    $finish;
  end
  initial begin #1000000;$fatal(1,"watchdog");end
endmodule
