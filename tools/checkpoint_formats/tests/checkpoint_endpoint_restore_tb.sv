`timescale 1ns/1ps
module checkpoint_endpoint_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer ADDR_BITS=32, ID_BITS=`NASTI_ID_BITS;
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
  CheckpointEndpointComponent dut (
    .clock(clock), .reset(reset),
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
    checks++; if(!cond) begin $display("ENDPOINT_RESTORE_DIVERGENCE %s",why);
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
  task prepare_cut(input integer which);
    integer d;begin
      // Drain complete handshakes, retaining every stalled master payload.
      // Supply only the missing half of a pre-existing partial write.
      for(d=0;d<200;d++)begin
        bready=1;rready=1;requestReady=1;streamReady=1;
        if(dmaTaken)dmaValid=0;
        if(awTaken)awvalid=0;if(wTaken)wvalid=0;if(arTaken)arvalid=0;
        if(dut.adapter.haveAW&&!dut.adapter.haveW&&!wvalid)begin wvalid=1;wdata=1;end
        if(dut.adapter.haveW&&!dut.adapter.haveAW&&!awvalid)begin awvalid=1;awaddr=8'h20;awid=1;end
        tick();@(negedge clock);
        if(!dut.adapter.haveAW&&!dut.adapter.haveW&&!dut.adapter.haveAR&&
           !dut.adapter.busy&&!dut.adapter.responseValid&&!responseValid&&delay==0&&
           (!awvalid||awTaken)&&(!wvalid||wTaken)&&(!arvalid||arTaken))break;
      end
      check(d<200,"drain finite protocol obligations before selected cut");
      awvalid=0;wvalid=0;arvalid=0;dmaValid=0;awTaken=0;wTaken=0;arTaken=0;dmaTaken=0;
      bready=0;rready=0;
      if(which==0||which==4)begin
        awvalid=1;awaddr=8'h70;awid=3;
        if(which==4)begin wvalid=1;wdata=32'h1234;end
        tick();@(negedge clock);
        check(awTaken&&(which!=4||wTaken),"selected AW/W handshake");
        awvalid=0;wvalid=0;
      end
      if(which==1||which==2||which==3)begin
        arvalid=1;araddr=which==3?8'h24:8'h60;arid=7;
        tick();@(negedge clock);check(arTaken,"selected AR handshake");arvalid=0;
      end
      if(which==2||which==3||which==4)begin
        for(d=0;d<30;d++)begin
          if(reached(which))break;
          tick();@(negedge clock);
        end
        check(d<30,"selected response obligation finite setup");
      end
      if(which==5)begin dmaValid=1;streamReady=0;dmaTaken=0;end
    end
  endtask
  function automatic bit reached(input integer which);
    begin case(which)
      0:reached=dut.adapter.haveAW&&!dut.adapter.haveW;
      1:reached=dut.adapter.haveAR&&!dut.adapter.haveAW&&!dut.adapter.haveW;
      2:reached=dut.localValid&&dut.adapter.busy;
      3:reached=dut.adapter.busy&&!dut.localValid&&delay>0;
      4:reached=dut.adapter.responseValid&&dut.adapter.writing&&!bready;
      5:reached=dut.producedFrames>0&&dmaValid&&!streamReady;
      default:reached=0;
    endcase end
  endfunction
  integer cut=0, fd, tf, trial, bitno, warm, i, got, corrupt=0;
  integer reads=0,writes=0,backend=0,frames=0,held=0,goodReads=0,goodWrites=0;
  reg [106+2*ID_BITS:0] savedMaster;
  reg [757:0] saved, random_state, before_state;
  reg savedResponseValid,savedResponseError;
  reg [31:0] savedResponseData;
  integer savedDelay,savedCommands;
  string image, save, trace, corruptName;
  initial begin
    $dumpfile("endpoint-restore.vcd"); $dumpvars(0,checkpoint_endpoint_restore_tb);
    void'($value$plusargs("CUT=%d",cut)); void'($value$plusargs("TRACE=%s",trace));
    void'($value$plusargs("CORRUPT=%s",corruptName));
    repeat(3)tick(); @(negedge clock); reset=0; restore_hold=1; restore_load=1; restore_state=0;
    #1; check(restore_accepted&&!restore_error,"initial complete original-register initialization");
    tick(); @(negedge clock); restore_load=0;
    // Complete original register and geometry-padding tests use no force/deposit.
    for(trial=0;trial<32;trial++) begin
      for(i=0;i<758;i++) random_state[i]=noise(trial*31+i)&1;
      // 758-bit vector has zero padding in the canonical adapter address/ID slots.
      random_state[228+32+:32]=0; random_state[228+93+ID_BITS+:64-ID_BITS]=0;
      random_state[228+191+ID_BITS+:64-ID_BITS]=0;
      random_state[228+260+32+:32]=0; random_state[228+353+ID_BITS+:64-ID_BITS]=0;
      random_state[228+458+ID_BITS+:64-ID_BITS]=0;
      restore_state=random_state; restore_load=1; #1;
      check(restore_accepted&&!restore_error,"complete endpoint arbitrary canonical load"); parked();
      tick(); check(control_state===random_state && expected_state===random_state,"complete original-register canonical readback");
      @(negedge clock); restore_load=0;
    end
    saved=expected_state;
    // All geometry padding bits reject before either locals or adapter change.
    for(bitno=0;bitno<530;bitno++) begin
      if((bitno>=32&&bitno<64)||(bitno>=93+ID_BITS&&bitno<157)||
         (bitno>=191+ID_BITS&&bitno<255)||(bitno>=292&&bitno<324)||
         (bitno>=353+ID_BITS&&bitno<417)||(bitno>=458+ID_BITS&&bitno<522)) begin
        restore_state=saved; restore_state[228+bitno]=1; restore_load=1; #1;
        check(!restore_accepted&&restore_error,"endpoint padding rejection"); parked();
        tick(); check(expected_state===saved,"padding rejected without any original mutation");
        @(negedge clock); restore_load=0;
      end
    end
    // Hold all local side-effect sources active: DMA, abort, AXI and backend.
    awvalid=1;wvalid=1;arvalid=1;bready=1;rready=1;dmaValid=1;dmaAbort=1;streamReady=1;
    repeat(5) begin #1;parked();tick();check(expected_state===saved,"all locals and adapter held");@(negedge clock);end
    for(trial=0;trial<5;trial++) begin
      restore_state=saved ^ 758'h123456789abcdef; restore_load=1; restore_hold=trial!=0;
      ownersQuiescent=trial!=1; ownerError=trial==2; epoch=trial==3?43:42; reset=trial==4;
      #1;check(!restore_accepted&&restore_error,"load certificate rejection before mutation");parked();
      // Reset legitimately resets resettable registers, so sample only before its edge.
      if(trial!=4) begin tick();check(expected_state===saved,"certificate rejection preserves original state");end
      @(negedge clock);restore_load=0;reset=0;
    end
    // The local response owns arbitration if both response producers are
    // presented. Restore constructs the exact original busy/localValid state.
    ownersQuiescent=1;ownerError=0;epoch=42;restore_hold=1;restore_load=1;restore_state=0;
    restore_state[194]=1;restore_state[195+:32]=32'habcde123;restore_state[228+422]=1;
    #1;check(restore_accepted,"priority fixture canonical load");tick();@(negedge clock);
    restore_load=0;restore_hold=0;dmaValid=0;dmaAbort=0;
    responseValid=1;responseData=32'h87654321;responseError=1;delay=0;
    #1;check(dut.adapter.io_response_ready&&!responseReady,"local response prevents backend acknowledgement");
    tick();check(dut.adapter.responseValid&&dut.adapter.responseData==32'habcde123&&
      !dut.adapter.responseError&&!dut.localValid,"local response data and error retain priority");
    @(negedge clock);restore_hold=1;responseValid=0;responseError=0;responseData=0;
    ownersQuiescent=1;ownerError=0;epoch=42;restore_hold=1;restore_load=1;restore_state=0;
    tick();@(negedge clock);restore_load=0;dmaAbort=0;
    if($value$plusargs("IMAGE=%s",image)) begin
      fd=$fopen(image,"r");check(fd!=0,"open fixture image");
      got=$fscanf(fd,"%h %d %d %h %d %d %h %d\n",saved,savedResponseValid,savedResponseError,
        savedResponseData,savedDelay,savedCommands,savedMaster,warm);
      check(got==8,"complete component image");$fclose(fd);
      restore_state=saved;
      if(corruptName=="semantic")restore_state[194]=~restore_state[194];
      restore_load=1;#1;check(restore_accepted,"fresh endpoint certificate");parked();tick();
      check(expected_state===saved,"fresh complete original-register zero-edge readback");
      @(negedge clock);restore_load=0;
      responseValid=savedResponseValid;responseError=savedResponseError;responseData=savedResponseData;
      delay=savedDelay;commands=savedCommands;
      {dmaTaken,dmaValid,streamReady,bready,rready,awvalid,wvalid,arvalid,awaddr,araddr,wdata,awid,arid,awTaken,wTaken,arTaken}=savedMaster;
      check(reached(cut),"restored explicitly selected protocol cut");
    end else begin
      restore_hold=0;
      awvalid=0;wvalid=0;arvalid=0;awTaken=0;wTaken=0;arTaken=0;dmaTaken=0;dmaValid=0;
      for(i=0;i<300;i++)begin drive(i);tick();@(negedge clock);end
      prepare_cut(cut);
      check(reached(cut),"donor explicitly selected protocol cut");warm=1000+cut;
      savedMaster={dmaTaken,dmaValid,streamReady,bready,rready,awvalid,wvalid,arvalid,awaddr,araddr,wdata,awid,arid,awTaken,wTaken,arTaken};
      restore_hold=1;saved=expected_state;
      savedResponseValid=responseValid;savedResponseError=responseError;savedResponseData=responseData;
      savedDelay=delay;savedCommands=commands;
      check($value$plusargs("SAVE=%s",save),"save path");fd=$fopen(save,"w");
      $fdisplay(fd,"%h %d %d %h %d %d %h %d",saved,savedResponseValid,savedResponseError,savedResponseData,savedDelay,savedCommands,savedMaster,warm);$fclose(fd);

    end
    repeat(5)begin #1;parked();tick();check(expected_state===saved,"saved endpoint holds one epoch");@(negedge clock);end
    check(trace!="","trace path");tf=$fopen(trace,"w");restore_hold=0;
    for(i=0;i<2000;i++)begin
      drive(warm+i);#1;
      reads+=rvalid&&rready;writes+=bvalid&&bready;goodReads+=rvalid&&rready&&rresp==0;goodWrites+=bvalid&&bready&&bresp==0;backend+=requestValid&&requestReady;frames+=streamValid&&streamReady;
      $fdisplay(tf,"%0d %h %h %h",i,expected_state,
        {awready,wready,arready,bvalid,rvalid,bresp,rresp,bid,rid,rdata,rlast},
        {requestValid,requestWrite,requestAddress,requestData,responseReady,dmaReady,streamValid});
      tick();check(control_state===expected_state,"live canonical vector equals independent original registers");@(negedge clock);
    end
    $fclose(tf);check(reads>10&&writes>10&&backend>10&&frames>100&&goodReads>10&&goodWrites>10,"active local/backend/stream continuation");
    $display("ENDPOINT_RESTORE_PASS cut=%0d reads=%0d writes=%0d backend=%0d frames=%0d good_reads=%0d good_writes=%0d checks=%0d",cut,reads,writes,backend,frames,goodReads,goodWrites,checks);$finish;
  end
  initial begin #2000000;$fatal(1,"endpoint timeout");end
endmodule
