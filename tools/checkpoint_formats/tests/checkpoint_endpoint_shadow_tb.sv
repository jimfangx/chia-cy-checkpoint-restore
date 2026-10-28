`timescale 1ns/1ps
module checkpoint_endpoint_shadow_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer ADDR_BITS=32, ID_BITS=`NASTI_ID_BITS;
  localparam integer SHADOW_BITS=`SHADOW_BITS, STAGING_BITS=SHADOW_BITS+97, WORDS=(SHADOW_BITS+63)/64;
  reg [STAGING_BITS-1:0] shadow_state=0;
  wire [STAGING_BITS-1:0] shadow_current;
  reg [`CONTROL_BITS-1:0] transport_control=0;
  wire [STAGING_BITS-1:0] shadow_original={dut.snapshot.index,dut.snapshot.label,dut.snapshot.saved,dut.snapshot.occupied};
  wire [757:0] control_state;
  reg restore_hold=0, restore_load=0;
  reg [757:0] restore_state=0;
  wire restore_accepted, restore_error;
  integer state_checks=0, random_steps=0;
  reg randomize_metadata=0;
  reg [1:0] awburst=1, arburst=1;
  reg awlock=0, arlock=0, awuser=0, aruser=0, wuser=0;
  reg [3:0] awcache=0, arcache=0, awqos=0, arqos=0, awregion=0, arregion=0;
  reg [2:0] awprot=0, arprot=0;
  reg [ID_BITS-1:0] wid=0;
  reg clock = 0; always #5 clock = ~clock;
  reg reset = 1;
  reg awvalid=0, wvalid=0, arvalid=0, bready=0, rready=0;
  reg [ADDR_BITS-1:0] awaddr=0, araddr=0;
  reg [31:0] wdata=0;
  reg [7:0] awlen=0, arlen=0;
  reg [2:0] awsize=2, arsize=2;
  reg [ID_BITS-1:0] awid=3, arid=9;
  reg [3:0] strb=15;
  reg wlast=1;
  wire awready, wready, arready, bvalid, rvalid;
  wire [1:0] bresp, rresp;
  wire [ID_BITS-1:0] bid, rid;
  wire [31:0] rdata;
  wire rlast, requestValid, requestWrite, responseReady;
  wire [7:0] requestAddress;
  wire [31:0] requestData;
  reg requestReady=1, responseValid=0, responseError=0;
  reg [31:0] responseData=0;
  integer commands=0, checks=0, timeout=0;
  reg [63:0] epoch=42;
  reg ownersQuiescent=1, ownerError=0;
  reg dmaValid=0, dmaAbort=0, streamReady=1, frozen=0;
  wire dmaReady, streamValid;
  wire [511:0] streamData;
  CheckpointEndpointShadowComponent dut (
    .clock(clock), .reset(reset), .io_control(transport_control), .io_cutValid(1'b1),
    .io_restore_shadow_state(shadow_state), .io_restore_shadow_current(shadow_current),
    .io_restore_epoch(epoch), .io_restore_expectedEpoch(64'd42),
    .io_restore_ownersQuiescent(ownersQuiescent), .io_restore_ownerError(ownerError),
    .io_stream_valid(streamValid), .io_stream_ready(streamReady), .io_stream_bits(streamData),
    .io_dmaValid(dmaValid), .io_dmaReady(dmaReady), .io_dmaData(512'h123456),
    .io_dmaAbort(dmaAbort), .io_frozen(frozen), .io_state(control_state),
    .io_restore_hold(restore_hold), .io_restore_load(restore_load),
    .io_restore_state(restore_state), .io_restore_accepted(restore_accepted), .io_restore_error(restore_error),
    .io_ctrl_aw_valid(awvalid), .io_ctrl_aw_ready(awready),
    .io_ctrl_aw_bits_addr(awaddr), .io_ctrl_aw_bits_id(awid),
    .io_ctrl_aw_bits_len(awlen), .io_ctrl_aw_bits_size(awsize),
    .io_ctrl_aw_bits_burst(awburst), .io_ctrl_aw_bits_lock(awlock),
    .io_ctrl_aw_bits_cache(awcache), .io_ctrl_aw_bits_prot(awprot),
    .io_ctrl_aw_bits_qos(awqos), .io_ctrl_aw_bits_region(awregion), .io_ctrl_aw_bits_user(awuser),
    .io_ctrl_w_valid(wvalid), .io_ctrl_w_ready(wready),
    .io_ctrl_w_bits_data(wdata), .io_ctrl_w_bits_id(wid),
    .io_ctrl_w_bits_last(wlast), .io_ctrl_w_bits_strb(strb), .io_ctrl_w_bits_user(wuser),
    .io_ctrl_b_valid(bvalid), .io_ctrl_b_ready(bready), .io_ctrl_b_bits_id(bid), .io_ctrl_b_bits_resp(bresp),
    .io_ctrl_ar_valid(arvalid), .io_ctrl_ar_ready(arready),
    .io_ctrl_ar_bits_addr(araddr), .io_ctrl_ar_bits_id(arid),
    .io_ctrl_ar_bits_len(arlen), .io_ctrl_ar_bits_size(arsize),
    .io_ctrl_ar_bits_burst(arburst), .io_ctrl_ar_bits_lock(arlock),
    .io_ctrl_ar_bits_cache(arcache), .io_ctrl_ar_bits_prot(arprot),
    .io_ctrl_ar_bits_qos(arqos), .io_ctrl_ar_bits_region(arregion), .io_ctrl_ar_bits_user(aruser),
    .io_ctrl_r_valid(rvalid), .io_ctrl_r_ready(rready), .io_ctrl_r_bits_id(rid),
    .io_ctrl_r_bits_data(rdata), .io_ctrl_r_bits_resp(rresp), .io_ctrl_r_bits_last(rlast),
    .io_backendValid(requestValid), .io_backendReady(requestReady),
    .io_backendWrite(requestWrite), .io_backendAddress(requestAddress),
    .io_backendData(requestData), .io_responseValid(responseValid),
    .io_responseReady(responseReady), .io_responseData(responseData), .io_responseError(responseError)
  );
  wire [529:0] adapter_expected={dut.adapter.errorReadRemaining,
    {{(64-ID_BITS){1'b0}},dut.adapter.responseId},
    dut.adapter.responseData,
    dut.adapter.responseError,
    dut.adapter.responseValid,
    dut.adapter.writing,
    dut.adapter.busy,
    dut.adapter.badW,
    dut.adapter.haveAR,
    dut.adapter.haveW,
    dut.adapter.haveAW,
    dut.adapter.ar_user,
    {{(64-ID_BITS){1'b0}},dut.adapter.ar_id},
    dut.adapter.ar_region,
    dut.adapter.ar_qos,
    dut.adapter.ar_prot,
    dut.adapter.ar_cache,
    dut.adapter.ar_lock,
    dut.adapter.ar_burst,
    dut.adapter.ar_size,
    dut.adapter.ar_len,
    {{(64-ADDR_BITS){1'b0}},dut.adapter.ar_addr},
    dut.adapter.wd_user,
    dut.adapter.wd_strb,
    {{(64-ID_BITS){1'b0}},dut.adapter.wd_id},
    dut.adapter.wd_last,
    dut.adapter.wd_data,
    dut.adapter.aw_user,
    {{(64-ID_BITS){1'b0}},dut.adapter.aw_id},
    dut.adapter.aw_region,
    dut.adapter.aw_qos,
    dut.adapter.aw_prot,
    dut.adapter.aw_cache,
    dut.adapter.aw_lock,
    dut.adapter.aw_burst,
    dut.adapter.aw_size,
    dut.adapter.aw_len,
    {{(64-ADDR_BITS){1'b0}},dut.adapter.aw_addr}};

  wire [757:0] expected_state={adapter_expected,dut.localError,dut.localData,
    dut.localValid,dut.counterOverflow,dut.hostDrainedFrames,dut.producedSnapshot,
    dut.producedFrames,dut.invalid};
  reg awTaken=0,wTaken=0,arTaken=0,dmaTaken=0;
  reg priorAW=0,priorW=0,priorAR=0,priorDMA=0;
  wire [ADDR_BITS+ID_BITS+29:0] masterAW={awaddr,awid,awlen,awsize,awburst,awlock,awcache,awprot,awqos,awregion,awuser};
  wire [ADDR_BITS+ID_BITS+29:0] masterAR={araddr,arid,arlen,arsize,arburst,arlock,arcache,arprot,arqos,arregion,aruser};
  wire [ID_BITS+37:0] masterW={wdata,wlast,wid,strb,wuser};
  reg [ADDR_BITS+ID_BITS+29:0] priorAWBits=0,priorARBits=0;
  reg [ID_BITS+37:0] priorWBits=0;
  always @(posedge clock) begin
    if(reset || restore_hold || restore_load) begin priorAW<=0;priorW<=0;priorAR<=0;priorDMA<=0;end
    else begin
      if(priorAW && (!awvalid || masterAW!==priorAWBits))$fatal(1,"unstable AW while stalled");
      if(priorW && (!wvalid || masterW!==priorWBits))$fatal(1,"unstable W while stalled");
      if(priorAR && (!arvalid || masterAR!==priorARBits))$fatal(1,"unstable AR while stalled");
      if(priorDMA && !dmaValid)$fatal(1,"unstable DMA valid while stalled");
      priorDMA<=dmaValid&&!dmaReady;dmaTaken<=dmaValid&&dmaReady;
      priorAW<=awvalid&&!awready;priorW<=wvalid&&!wready;priorAR<=arvalid&&!arready;
      priorAWBits<=masterAW;priorWBits<=masterW;priorARBits<=masterAR;
      awTaken<=awvalid&&awready;wTaken<=wvalid&&wready;arTaken<=arvalid&&arready;
    end
  end
  integer delay=0;
  always @(posedge clock) begin
    if (reset) begin responseValid<=0; delay<=0; commands<=0; responseData<=0; responseError<=0; end
    else if (!restore_hold && !restore_load) begin
      if (responseValid && responseReady) responseValid<=0;
      if (requestValid && requestReady) begin
        if(delay || responseValid) $fatal(1,"multiple backend obligations");
        commands<=commands+1; delay<=3;
        responseData<={24'h765432,requestAddress}; responseError<=requestAddress==8'hfc;
      end
      if(delay>0) begin delay<=delay-1; if(delay==1)responseValid<=1; end
    end
  end
  task tick; begin @(posedge clock); #1; end endtask
  task check(input bit cond, input string why); begin
    checks++; if(!cond) begin $display("ENDPOINT_SHADOW_DIVERGENCE %s",why);
      $dumpflush; checkpoint_widget_failed(); $finish; end
  end endtask
  task parked; begin
    check(!awready && !wready && !arready && !bvalid && !rvalid &&
      !requestValid && !responseReady && !dmaReady && !streamValid,
      "common epoch hold masks all endpoint handshakes");
  end endtask
  function automatic [31:0] noise(input integer cycle);
    reg [31:0] x; begin x=cycle*32'h9e3779b9+32'h34345; x=x^(x>>13); x=x^(x<<17); noise=x^(x>>5); end
  endfunction
  task drive(input integer cycle);
    reg [31:0] x; begin
      x=noise(cycle); bready=x[3]; rready=x[4];
      if(!dmaValid||dmaTaken)dmaValid=x[5]; streamReady=x[6]; dmaAbort=cycle==71; requestReady=x[7];
      if(!awvalid||awTaken)begin
        awvalid=x[0];awid=x>>16;
        case(x[11:8]%8)
          0:awaddr=8'h70;1:awaddr=8'h74;2:awaddr=8'h64;3:awaddr=0;default:awaddr=8'h20;
        endcase
      end
      if(!wvalid||wTaken)begin wvalid=x[1];wdata=cycle%3==0?1:x;end
      if(!arvalid||arTaken)begin
        arvalid=x[2];arid=x>>20;
        case(x[15:12]%7)
          0:araddr=8'h60;1:araddr=8'h68;2:araddr=8'h6c;3:araddr=8'h70;
          4:araddr=8'h74;default:araddr=8'h24;
        endcase
      end
    end
  endtask
  task load_check;
    begin
      #1;check(restore_accepted&&!restore_error,"all fifty registers accept one epoch");parked();
      tick();check(expected_state===restore_state && shadow_original===shadow_state &&
        control_state===expected_state && shadow_current===shadow_original,
        "complete fifty-register independent zero-edge readback");
      @(negedge clock);restore_load=0;
    end
  endtask
  task write_local(input [7:0] addr,input [31:0] value,input bit expectedError);
    bit a,w;integer waitCycles;
    begin
      awvalid=1;awaddr=addr;awid=3;wvalid=1;wdata=value;bready=0;a=0;w=0;
      for(waitCycles=0;waitCycles<100;waitCycles++)begin
        #1;if(awvalid&&awready)a=1;if(wvalid&&wready)w=1;
        tick();@(negedge clock);if(a)awvalid=0;if(w)wvalid=0;if(a&&w)break;
      end
      check(a&&w,"write address/data accepted");
      for(waitCycles=0;waitCycles<100;waitCycles++)begin #1;if(bvalid)break;tick();@(negedge clock);end
      check(bvalid&&bresp==(expectedError?2:0),"shadow write response/error");
      bready=1;tick();@(negedge clock);bready=0;
    end
  endtask
  reg [31:0] lastRead;
  task read_local(input [7:0] addr);
    integer waitCycles;bit a;
    begin
      arvalid=1;araddr=addr;arid=7;rready=0;a=0;
      for(waitCycles=0;waitCycles<100;waitCycles++)begin
        #1;if(arvalid&&arready)a=1;tick();@(negedge clock);if(a)begin arvalid=0;break;end
      end
      check(a,"read address accepted");
      for(waitCycles=0;waitCycles<100;waitCycles++)begin #1;if(rvalid)break;tick();@(negedge clock);end
      check(rvalid&&rresp==0,"shadow read response");lastRead=rdata;
      rready=1;tick();@(negedge clock);rready=0;
    end
  endtask
  integer i,trial,fd,tf,got,word,negative=0;
  reg [757:0] saved,random_state;
  reg [STAGING_BITS-1:0] savedShadow;
  reg [SHADOW_BITS-1:0] payload;
  reg [63:0] expectedWord;
  string image,save,trace,corrupt;
  initial begin
    $dumpfile("endpoint-shadow.vcd");$dumpvars(0,checkpoint_endpoint_shadow_tb);
    void'($value$plusargs("TRACE=%s",trace));void'($value$plusargs("CORRUPT=%s",corrupt));
    repeat(3)tick();@(negedge clock);reset=0;restore_hold=1;restore_load=1;load_check();
    for(trial=0;trial<64;trial++)begin
      for(i=0;i<758;i++)random_state[i]=noise(trial*31+i)&1;
      random_state[228+32+:32]=0;random_state[228+93+ID_BITS+:64-ID_BITS]=0;
      random_state[228+191+ID_BITS+:64-ID_BITS]=0;random_state[228+292+:32]=0;
      random_state[228+353+ID_BITS+:64-ID_BITS]=0;random_state[228+458+ID_BITS+:64-ID_BITS]=0;
      for(i=0;i<STAGING_BITS;i++)shadow_state[i]=noise(trial*43+i)&1;
      shadow_state[SHADOW_BITS+65+:32]=trial%WORDS;
      restore_state=random_state;restore_load=1;load_check();
    end
    saved=expected_state;savedShadow=shadow_original;
    // Invalid staging indices reject the WHOLE transaction, including the
    // otherwise valid and deliberately different original endpoint payload.
    for(trial=0;trial<34;trial++)begin
      shadow_state=savedShadow;
      shadow_state[SHADOW_BITS+65+:32]=trial==32?WORDS:trial==33?32'hffffffff:(32'h1<<trial)|WORDS;
      restore_state=saved^758'h12345;restore_load=1;#1;
      check(!restore_accepted&&restore_error,"invalid shadow index rejects common epoch");parked();
      tick();check(expected_state===saved&&shadow_original===savedShadow,"shadow rejection is atomic");
      @(negedge clock);restore_load=0;negative++;
    end
    shadow_state=savedShadow^1;restore_state=saved;restore_state[228+32]=1;restore_load=1;#1;
    check(!restore_accepted&&restore_error,"adapter padding rejects staging load");parked();
    tick();check(expected_state===saved&&shadow_original===savedShadow,"adapter rejection is atomic");
    @(negedge clock);restore_load=0;negative++;
    for(trial=0;trial<4;trial++)begin
      shadow_state=savedShadow^1;restore_state=saved^1;restore_load=1;
      restore_hold=trial!=0;ownersQuiescent=trial!=1;ownerError=trial==2;epoch=trial==3?43:42;#1;
      check(!restore_accepted&&restore_error,"owner/epoch rejection covers staging");parked();
      tick();check(expected_state===saved&&shadow_original===savedShadow,"certificate rejection is atomic");
      @(negedge clock);restore_load=0;negative++;
    end
    ownersQuiescent=1;ownerError=0;epoch=42;restore_hold=1;
    restore_state=0;shadow_state=0;restore_load=1;load_check();
    // Reset wins over a valid staging load and immediately hides old history.
    shadow_state[0]=1;restore_load=1;reset=1;#1;
    check(!restore_accepted&&restore_error,"reset rejects common load");parked();tick();
    check(shadow_original==0,"reset priority over staging load");
    @(negedge clock);reset=0;restore_load=0;shadow_state=0;
    restore_state=0;restore_load=1;load_check();
    transport_control[339+:3]=2;transport_control[342+:64]=42;
    if($value$plusargs("IMAGE=%s",image))begin
      fd=$fopen(image,"r");check(fd!=0,"open complete fixture image");
      got=$fscanf(fd,"%h %h\n",saved,savedShadow);$fclose(fd);check(got==2,"read both independent state vectors");
      restore_state=saved;shadow_state=savedShadow;
      if(corrupt=="semantic")shadow_state[1]=~shadow_state[1];
      restore_load=1;#1;check(restore_accepted,"fresh full restore accepted");parked();tick();
      check(expected_state===saved&&shadow_original===savedShadow,"fresh complete fifty-register zero-edge readback");
      @(negedge clock);restore_load=0;
    end else begin
      restore_hold=0;write_local('h78,1,0);write_local('h7c,7,0);
      check(dut.snapshot.occupied&&dut.snapshot.index==7&&dut.snapshot.label==42,"active occupied partially read capture");
      // The saved source remains immutable while live source words change.
      transport_control=~transport_control;read_local('h80);
      restore_hold=1;saved=expected_state;savedShadow=shadow_original;
      check($value$plusargs("SAVE=%s",save),"save complete fixture path");fd=$fopen(save,"w");
      $fdisplay(fd,"%h %h",saved,savedShadow);$fclose(fd);
    end
    repeat(5)begin #1;parked();tick();check(expected_state===saved&&shadow_original===savedShadow,"all owners held");@(negedge clock);end
    payload=savedShadow[SHADOW_BITS:1];restore_hold=0;
    check(trace!="","trace path");tf=$fopen(trace,"w");
    for(i=0;i<4*WORDS;i++)begin
      word=(i*7)%WORDS;write_local('h7c,word,0);expectedWord=payload>>(word*64);
      read_local('h80);check(lastRead===expectedWord[31:0],"restored indexed low payload");
      $fdisplay(tf,"%d %h %h %h",i,lastRead,expected_state,shadow_original);
      read_local('h84);check(lastRead===expectedWord[63:32],"restored indexed high payload");
      $fdisplay(tf,"%d %h %h %h",i,lastRead,expected_state,shadow_original);
      write_local('h78,1,1);check(dut.snapshot.saved===payload,"rejected recapture preserves history");
    end
    read_local('h8c);check(lastRead==42,"restored cut label");
    write_local('h78,2,0);read_local('h88);check(lastRead==0,"release restored occupied history");
    $fclose(tf);$display("ENDPOINT_SHADOW_PASS bits=%d words=%d negative=%d checks=%d",SHADOW_BITS,WORDS,negative,checks);$finish;
  end
  initial begin #2000000;$fatal(1,"endpoint shadow timeout");end
endmodule
