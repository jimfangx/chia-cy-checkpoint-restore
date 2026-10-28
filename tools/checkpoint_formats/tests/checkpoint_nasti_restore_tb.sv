`timescale 1ns/1ps
module checkpoint_nasti_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer ADDR_BITS=`NASTI_ADDR_BITS, ID_BITS=`NASTI_ID_BITS;
  wire [529:0] control_state;
  reg restore_hold=0, restore_load=0;
  reg [529:0] restore_state=0;
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
  CheckpointNastiAdapter dut (
    .clock(clock), .reset(reset), .io_controlState(control_state),
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
    .io_request_valid(requestValid), .io_request_ready(requestReady),
    .io_request_bits_write(requestWrite), .io_request_bits_address(requestAddress),
    .io_request_bits_data(requestData), .io_response_valid(responseValid),
    .io_response_ready(responseReady), .io_response_bits_data(responseData), .io_response_bits_error(responseError)
  );
  // Variable-latency backend response, held until accepted; no write side effects
  // are permitted for invalid AXI metadata, strobes or malformed bursts.
  integer delay=0;
  always @(posedge clock) begin
    if (reset) begin responseValid<=0; delay<=0; commands<=0; end
    else if (!restore_hold && !restore_load) begin
      if (responseValid && responseReady) responseValid<=0;
      if (requestValid && requestReady) begin
        if (delay || responseValid) $fatal(1,"multiple backend requests");
        commands<=commands+1;
        delay<=3;
        responseData<={24'h123456,requestAddress};
        responseError<=requestAddress==8'hfc;
      end
      if (delay>0) begin
        delay<=delay-1;
        if (delay==1) responseValid<=1;
      end
    end
  end
  task tick; begin @(posedge clock); #1; end endtask
  task check(input bit cond, input string why); begin
    checks=checks+1; if (!cond) begin $display("NASTI_RESTORE_DIVERGENCE %s",why); $dumpflush; checkpoint_widget_failed(); $finish; end
  end endtask
  task aw(input [31:0] addr); begin
    @(negedge clock); awaddr=addr; awvalid=1;
    do tick(); while (!dut.haveAW);
    @(negedge clock); awvalid=0;
  end endtask
  task w(input [31:0] data, input bit last); begin
    @(negedge clock); wdata=data; wlast=last; wvalid=1;
    do begin @(posedge clock); end while (!wready);
    #1; @(negedge clock); wvalid=0;
  end endtask
  task ar(input [31:0] addr); begin
    @(negedge clock); araddr=addr; arvalid=1;
    do tick(); while (!dut.haveAR);
    @(negedge clock); arvalid=0;
  end endtask
  task b(input [1:0] expected); begin
    while (!bvalid) tick();
    repeat(4) begin tick(); check(bvalid && bresp==expected && bid==awid,"held B response"); end
    @(negedge clock); bready=1; tick(); @(negedge clock); bready=0;
  end endtask
  task r(input [1:0] expected, input bit last, input [31:0] data); begin
    while (!rvalid) tick();
    repeat(3) begin tick(); check(rvalid && rresp==expected && rid==arid && rlast==last,"held R response"); end
    if (expected==0) check(rdata==data,"read data");
    @(negedge clock); rready=1; tick(); @(negedge clock); rready=0;
  end endtask
  wire [529:0] expected_state={dut.errorReadRemaining,
    {{(64-ID_BITS){1'b0}},dut.responseId},
    dut.responseData,
    dut.responseError,
    dut.responseValid,
    dut.writing,
    dut.busy,
    dut.badW,
    dut.haveAR,
    dut.haveW,
    dut.haveAW,
    dut.ar_user,
    {{(64-ID_BITS){1'b0}},dut.ar_id},
    dut.ar_region,
    dut.ar_qos,
    dut.ar_prot,
    dut.ar_cache,
    dut.ar_lock,
    dut.ar_burst,
    dut.ar_size,
    dut.ar_len,
    {{(64-ADDR_BITS){1'b0}},dut.ar_addr},
    dut.wd_user,
    dut.wd_strb,
    {{(64-ID_BITS){1'b0}},dut.wd_id},
    dut.wd_last,
    dut.wd_data,
    dut.aw_user,
    {{(64-ID_BITS){1'b0}},dut.aw_id},
    dut.aw_region,
    dut.aw_qos,
    dut.aw_prot,
    dut.aw_cache,
    dut.aw_lock,
    dut.aw_burst,
    dut.aw_size,
    dut.aw_len,
    {{(64-ADDR_BITS){1'b0}},dut.aw_addr}};
  always @(negedge clock) begin
    #1;
    if(!reset && !restore_hold && !restore_load && !$isunknown(expected_state)) begin
      check(control_state===expected_state,"complete canonical original register vector");
      state_checks++;
    end
  end
  // This layout is an independent original-register oracle. The restore
  // consumer/producer's exported vector is never used as the saved image.
  localparam [529:0] PADDING={8'b0, {(64-ID_BITS){1'b1}}, {ID_BITS{1'b0}}, 40'b0,
    1'b0, {(64-ID_BITS){1'b1}}, {ID_BITS{1'b0}}, 29'b0,
      {(64-ADDR_BITS){1'b1}}, {ADDR_BITS{1'b0}},
    5'b0, {(64-ID_BITS){1'b1}}, {ID_BITS{1'b0}}, 33'b0,
    1'b0, {(64-ID_BITS){1'b1}}, {ID_BITS{1'b0}}, 29'b0,
      {(64-ADDR_BITS){1'b1}}, {ADDR_BITS{1'b0}}};
  reg [529:0] saved, before_load, changed;
  integer cut=0, f, count, bit_index, trials=0, rejected=0, held_checks=0;
  integer continuation, restored=0, saved_commands, saved_delay, seed_value;
  reg saved_response_valid, saved_response_error;
  reg [31:0] saved_response_data;
  reg [31:0] rng=32'h952e7b1d;
  string image="", save_image="", trace="", corruption="";
  integer trace_file;
  reg in_continuation=0, aw_taken=0, w_taken=0, ar_taken=0;
  reg legal_metadata;
  wire [ADDR_BITS+ID_BITS+29:0] aw_payload={awaddr,awid,awlen,awsize,awburst,awlock,awcache,awprot,awqos,awregion,awuser};
  wire [ADDR_BITS+ID_BITS+29:0] ar_payload={araddr,arid,arlen,arsize,arburst,arlock,arcache,arprot,arqos,arregion,aruser};
  wire [ID_BITS+37:0] w_payload={wdata,wid,wlast,strb,wuser};
  reg [ADDR_BITS+ID_BITS+29:0] prior_aw=0,prior_ar=0;
  reg [ID_BITS+37:0] prior_w=0;
  reg prior_aw_stall=0,prior_ar_stall=0,prior_w_stall=0;
  integer cont_reads=0, cont_writes=0, cont_responses=0;
  integer cont_good_reads=0, cont_good_writes=0, cont_stalls=0;
  always @(posedge clock) begin
    aw_taken <= awvalid && awready;
    w_taken <= wvalid && wready;
    ar_taken <= arvalid && arready;
    if(in_continuation) begin
      if(prior_aw_stall) check(awvalid && aw_payload===prior_aw,"master AW payload changed under backpressure");
      if(prior_w_stall) check(wvalid && w_payload===prior_w,"master W payload changed under backpressure");
      if(prior_ar_stall) check(arvalid && ar_payload===prior_ar,"master AR payload changed under backpressure");
      prior_aw <= aw_payload; prior_w <= w_payload; prior_ar <= ar_payload;
      prior_aw_stall <= awvalid && !awready;
      prior_w_stall <= wvalid && !wready;
      prior_ar_stall <= arvalid && !arready;
      if(requestValid && requestReady) begin
        if(requestWrite) cont_writes <= cont_writes+1;
        else cont_reads <= cont_reads+1;
      end
      if(responseValid && responseReady) cont_responses <= cont_responses+1;
      if(rvalid && rready && rresp==0) cont_good_reads <= cont_good_reads+1;
      if(bvalid && bready && bresp==0) cont_good_writes <= cont_good_writes+1;
      if(requestValid && !requestReady) cont_stalls <= cont_stalls+1;
    end
  end
  function automatic [31:0] next_random();
    rng = rng ^ (rng << 13);
    rng = rng ^ (rng >> 17);
    rng = rng ^ (rng << 5);
    return rng;
  endfunction
  task no_handshake;
    check({awready,wready,arready,bvalid,rvalid,requestValid,responseReady}===7'b0,
      "restore barrier allowed a frontend/backend handshake");
  endtask
  task load_original(input [529:0] data);
    begin
      @(negedge clock); restore_hold=1; restore_load=1; restore_state=data; #1;
      check(restore_accepted && !restore_error,"valid load refused"); no_handshake();
      tick();
      // Independent complete readback, before either interface can advance.
      check(expected_state===data,"complete original-register readback before release");
      @(negedge clock); restore_load=0;
    end
  endtask
  task negative_load(input [529:0] data, input bit hold);
    begin
      @(negedge clock); restore_hold=hold; restore_load=1; restore_state=data;
      before_load=expected_state; #1;
      check(!restore_accepted && restore_error,"invalid load accepted"); no_handshake();
      tick(); check(expected_state===before_load,"rejected load partially changed original registers");
      @(negedge clock); restore_load=0; restore_hold=1; rejected++;
    end
  endtask
  initial begin
    $dumpfile("adapter-restore.vcd"); $dumpvars(0,checkpoint_nasti_restore_tb);
    seed_value=$value$plusargs("CUT=%d",cut);
    seed_value=$value$plusargs("IMAGE=%s",image);
    seed_value=$value$plusargs("SAVE=%s",save_image);
    seed_value=$value$plusargs("TRACE=%s",trace);
    seed_value=$value$plusargs("CORRUPT=%s",corruption);
    check(cut>=0 && cut<6,"unknown component cut");
    repeat(3) tick(); @(negedge clock); restore_hold=1; reset=0;
    if (image!="") begin
      f=$fopen(image,"r"); check(f!=0,"missing component image");
      count=$fscanf(f,"%h %d %d %d %d %h\n",saved,saved_commands,saved_delay,
        saved_response_valid,saved_response_error,saved_response_data);
      check(count==6,"truncated component image");
      // Refuse trailing bytes: this fixture image is not a .fsckpt format.
      count=$fgetc(f); check(count==-1,"trailing component image bytes"); $fclose(f);
      check((saved & PADDING)==0,"incompatible component geometry");
      changed=saved;
      if (corruption=="semantic") changed[426]=!changed[426];
      load_original(changed);
      // A distinct image oracle must reject semantic corruption before release.
      check(expected_state===saved,"saved-image semantic readback before release");
      commands=saved_commands; delay=saved_delay; responseValid=saved_response_valid;
      responseError=saved_response_error; responseData=saved_response_data;
      restored=1;
    end else begin
      load_original(0);
      // Exercise every canonical original bit with unrelated full-state data.
      // Padding zeros are checked independently of the implementation's schema.
      for(trials=0;trials<64;trials++) begin
        for(bit_index=0;bit_index<530;bit_index++) changed[bit_index]=next_random()>>31;
        changed=changed & ~PADDING; load_original(changed);
      end
      for(bit_index=0;bit_index<530;bit_index++) if(PADDING[bit_index])
        negative_load(changed | (530'b1<<bit_index),1);
      negative_load(changed,0);
      // Reset dominates the accepted pulse even with a valid load held high.
      @(negedge clock); reset=1; restore_load=1; restore_state=0; #1;
      check(!restore_accepted && restore_error,"load acknowledged during reset"); no_handshake();
      tick(); @(negedge clock); reset=0; restore_load=0;
      load_original(0);
      // Reset every test-backend owner too before preparing real protocol state.
      commands=0; delay=0; responseValid=0; responseError=0; responseData=0;
      @(negedge clock); restore_hold=0;
      case(cut)
        0: begin aw(32'h12340000); ar(32'h12340004); end
        1: begin awlen=1; aw(0); w(32'hcfed129a,0); ar(4); end
        2: begin requestReady=0; aw(0); w(32'hdb1375ec,1);
          @(negedge clock); requestReady=1; tick(); end
        3: begin aw(0); w(32'h3210fa78,1); while(!bvalid) tick(); end
        4: begin arlen=3; ar(4); r(2,0,0); end
        5: begin requestReady=0; ar(4); repeat(2) tick(); end
      endcase
      @(negedge clock); restore_hold=1; #1;
      case(cut)
        0: check(dut.haveAW && dut.haveAR && !dut.haveW,"partial AW and queued AR cut");
        1: check(dut.haveAW && dut.badW && !dut.haveW && dut.haveAR,"malformed W draining cut");
        2: check(dut.busy && delay>0 && !responseValid,"outstanding backend cut");
        3: check(dut.responseValid && dut.writing,"held B response cut");
        4: check(dut.responseValid && !dut.writing && dut.errorReadRemaining==2,"partial error R burst cut");
        5: check(dut.haveAR && !dut.busy,"backpressured backend request cut");
      endcase
      saved=expected_state; check(!$isunknown(saved),"unknown source register in component image");
      check(control_state===saved,"producer observation differs from original registers");
      check(save_image!="","save destination missing");
      saved_commands=commands; saved_delay=delay; saved_response_valid=responseValid;
      saved_response_error=responseError; saved_response_data=responseData;
      f=$fopen(save_image,"w"); check(f!=0,"save open");
      $fdisplay(f,"%h %0d %0d %0d %0d %h",saved,commands,delay,responseValid,responseError,responseData);
      $fclose(f);
    end
    // All handshakes remain disabled through adversarial external readiness.
    awvalid=1; wvalid=1; arvalid=1; bready=1; rready=1;
    requestReady=1; responseValid=1;
    before_load=expected_state;
    repeat(5) begin tick(); no_handshake();
      check(expected_state===before_load,"original state advanced during hold"); held_checks++;
    end
    // Restore the backend owner's saved state after the adversarial stimulus.
    responseValid=saved_response_valid;
    @(negedge clock); awvalid=0; wvalid=0; arvalid=0; bready=0; rready=0;
    restore_hold=0; in_continuation=1; rng=32'h952e7b1d;
    trace_file=$fopen(trace,"w"); check(trace_file!=0,"continuation trace open");
    for(continuation=0;continuation<3000;continuation++) begin
      if(continuation>0) @(negedge clock);
      // Each master channel holds VALID and all payload bits until accepted.
      // Mix legal AXI-lite traffic with bounded malformed bursts/metadata.
      if(!awvalid || aw_taken) begin
        awvalid=next_random()>>31; legal_metadata=(next_random() & 3)!=0;
        awaddr={next_random(),next_random()}; awid={next_random(),next_random()};
        awlen=next_random() & 1; awsize=next_random(); awburst=next_random(); awlock=next_random();
        awcache=next_random(); awprot=next_random(); awqos=next_random();
        awregion=next_random(); awuser=next_random();
        if(legal_metadata) begin awaddr[1:0]=0; awlen=0; awsize=2; awburst=1; awlock=0; end
      end
      if(!wvalid || w_taken) begin
        wvalid=next_random()>>31; legal_metadata=(next_random() & 3)!=0;
        wdata=next_random(); wid={next_random(),next_random()}; wlast=next_random()>>31;
        strb=next_random(); wuser=next_random();
        if(legal_metadata) begin wlast=1; strb=15; end
      end
      if(!arvalid || ar_taken) begin
        arvalid=next_random()>>31; legal_metadata=(next_random() & 3)!=0;
        araddr={next_random(),next_random()}; arid={next_random(),next_random()};
        arlen=next_random() & 3; arsize=next_random(); arburst=next_random(); arlock=next_random();
        arcache=next_random(); arprot=next_random(); arqos=next_random();
        arregion=next_random(); aruser=next_random();
        if(legal_metadata) begin araddr[1:0]=0; arlen=0; arsize=2; arburst=1; arlock=0; end
      end
      bready=next_random()>>31; rready=next_random()>>31; requestReady=next_random()>>31;
      #1;
      // Settled outputs and original state are sampled before the acknowledging
      // edge. Python compares every line against the continued donor process.
      $fdisplay(trace_file,"%0d %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h",
        continuation,expected_state,awready,wready,arready,bvalid,bid,bresp,
        rvalid,rid,rdata,rresp,rlast,requestValid,requestWrite,requestAddress,requestData,
        responseReady,delay,responseValid,commands,
        {awvalid,awaddr,awid,awlen,awsize,awburst,awlock,awcache,awprot,awqos,awregion,awuser,
         wvalid,wdata,wid,wlast,strb,wuser,arvalid,araddr,arid,arlen,arsize,arburst,arlock,arcache,
         arprot,arqos,arregion,aruser,bready,rready,requestReady,responseData,responseError});
      tick();
    end
    $fclose(trace_file);
    check(cont_reads>=8 && cont_writes>=8 && cont_responses>=16 &&
      cont_good_reads>=8 && cont_good_writes>=8 && cont_stalls>=8,
      "continuation lacks active successful read/write/response/backpressure coverage");
    $display("NASTI_CONTINUATION_COVERAGE reads=%0d writes=%0d responses=%0d good_reads=%0d good_writes=%0d stalls=%0d",
      cont_reads,cont_writes,cont_responses,cont_good_reads,cont_good_writes,cont_stalls);
    check(state_checks>=3000,"incomplete continuation state observations");
    $display("NASTI_RESTORE_PASS addr=%0d id=%0d cut=%0d restored=%0d cycles=3000 trials=%0d rejected=%0d held=%0d checks=%0d",
      ADDR_BITS,ID_BITS,cut,restored,trials,rejected,held_checks,checks); $finish;
  end
  initial begin #1000000; $fatal(1,"watchdog timeout"); end
endmodule
