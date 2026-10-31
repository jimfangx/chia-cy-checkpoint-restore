`timescale 1ns/1ps
// Actual generated Chisel endpoint, actual native RTL and vendor clock model.
// Hierarchy is observed for independent readback; no force, deposit or restore.
module native_widget_endpoint_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=130, OWNER_BITS=283, RAW_BITS=760, VIEW_BITS=827;
  localparam integer SHADOW_BITS=1585, SHADOW_WORDS=25, CONTROL_WORDS=5, TOTAL_FRAMES=11;
  localparam [255:0] HASH=256'h1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef;
  reg clock=0, reset=1;
  always #5 clock=~clock;
  reg [759:0] probe_raw=0;
  reg [66:0] probe_bank=0;
  wire [826:0] probe_view;
  wire [759:0] probe_recovered_raw;
  wire [66:0] probe_recovered_bank;
  wire probe_acknowledged,probe_correct_high,probe_misleading_low;
  wire [826:0] literal_probe_view={probe_bank,probe_raw[759:694],probe_raw[282:0],probe_raw[693:283]};
  CheckpointNativeEndpointLayoutProbe layout_probe(.clock(clock),.reset(reset),
    .io_raw(probe_raw),.io_bank(probe_bank),.io_view(probe_view),
    .io_recoveredRaw(probe_recovered_raw),.io_recoveredBank(probe_recovered_bank),
    .io_acknowledged(probe_acknowledged),.io_correctHighCertificate(probe_correct_high),
    .io_misleadingLowCertificate(probe_misleading_low));
  reg [63:0] target_cycle=0;
  wire [2:0] ce={target_cycle[1],target_cycle[2],!target_cycle[0]};
  wire clock_mask,freeze,functional_hold,native_valid,native_failed;
  wire unused_root; wire [2:0] unused_gates,captured_ce;
  wire [63:0] native_cut_cycle;
  wire [129:0] snapshot_state;
  reg [129:0] live_state=0;
  reg owner_fault=0;
  wire [1:0] owner_present=3,owner_frozen={2{functional_hold}},owner_error={2{owner_fault}};
  // The endpoint explicitly requests the compiler's external clock network.
  // Use a real external BUFGCE, never the disabled compatibility clock output.
  wire target_clock;
  BUFGCE target_gate(.I(clock),.CE(!clock_mask),.O(target_clock));
  always @(posedge target_clock)if(reset)target_cycle<=0;else target_cycle<=target_cycle+1;
  wire [759:0] raw_state;
  wire [66:0] bank_state;
  wire [826:0] endpoint_view;
  wire [757:0] endpoint_state;
  wire [31:0] descriptor_entry;
  wire bank_request_valid,bank_request_ready,bank_response_ready;
  reg bank_response_valid=0;
  wire reader_idle=!bank_response_valid;
  assign bank_request_ready=!bank_response_valid;
  wire [7:0] bank;wire [15:0] slot;wire [31:0] address;
  wire [63:0] bank_response_data=64'h123456789abcdef0;
  wire stream_valid,stream_last,stream_abort;
  wire [511:0] stream_data;
  reg stream_ready=0;
  reg awvalid=0,wvalid=0,arvalid=0,bready=0,rready=0;
  reg [31:0] awaddr=0,wdata=0,araddr=0;
  wire awready,wready,arready,bvalid,rvalid,rlast;
  wire [1:0] bresp,rresp;wire [3:0] bid,rid;wire [31:0] rdata;
  CheckpointNativeWidgetEndpoint dut(
    .clock(clock),.reset(reset),
    .io_ctrl_aw_valid(awvalid),.io_ctrl_aw_ready(awready),.io_ctrl_aw_bits_addr(awaddr),
    .io_ctrl_aw_bits_id(4'd3),.io_ctrl_aw_bits_len(8'd0),.io_ctrl_aw_bits_size(3'd2),
    .io_ctrl_aw_bits_burst(2'd1),.io_ctrl_aw_bits_lock(1'b0),.io_ctrl_aw_bits_cache(4'd0),
    .io_ctrl_aw_bits_prot(3'd0),.io_ctrl_aw_bits_qos(4'd0),.io_ctrl_aw_bits_region(4'd0),.io_ctrl_aw_bits_user(1'b0),
    .io_ctrl_w_valid(wvalid),.io_ctrl_w_ready(wready),.io_ctrl_w_bits_data(wdata),
    .io_ctrl_w_bits_id(4'd0),.io_ctrl_w_bits_last(1'b1),.io_ctrl_w_bits_strb(4'hf),.io_ctrl_w_bits_user(1'b0),
    .io_ctrl_b_valid(bvalid),.io_ctrl_b_ready(bready),.io_ctrl_b_bits_id(bid),.io_ctrl_b_bits_resp(bresp),
    .io_ctrl_ar_valid(arvalid),.io_ctrl_ar_ready(arready),.io_ctrl_ar_bits_addr(araddr),
    .io_ctrl_ar_bits_id(4'd7),.io_ctrl_ar_bits_len(8'd0),.io_ctrl_ar_bits_size(3'd2),
    .io_ctrl_ar_bits_burst(2'd1),.io_ctrl_ar_bits_lock(1'b0),.io_ctrl_ar_bits_cache(4'd0),
    .io_ctrl_ar_bits_prot(3'd0),.io_ctrl_ar_bits_qos(4'd0),.io_ctrl_ar_bits_region(4'd0),.io_ctrl_ar_bits_user(1'b0),
    .io_ctrl_r_valid(rvalid),.io_ctrl_r_ready(rready),.io_ctrl_r_bits_id(rid),
    .io_ctrl_r_bits_data(rdata),.io_ctrl_r_bits_resp(rresp),.io_ctrl_r_bits_last(rlast),
    .io_stream_valid(stream_valid),.io_stream_ready(stream_ready),.io_stream_bits(stream_data),
    .io_streamLast(stream_last),.io_streamAbort(stream_abort),
    .io_native_ce(ce),.io_native_targetCycle(target_cycle),
    .io_native_ownerPresent(owner_present),.io_native_ownerFrozen(owner_frozen),.io_native_ownerError(owner_error),
    .io_native_readerIdle(reader_idle),.io_native_liveState(live_state),
    .io_native_rootClock(unused_root),.io_native_gateClock(unused_gates),.io_native_clockMask(clock_mask),
    .io_native_freeze(freeze),.io_native_functionalHold(functional_hold),.io_native_valid(native_valid),
    .io_native_failed(native_failed),.io_native_cutCycle(native_cut_cycle),.io_native_capturedCE(captured_ce),
    .io_native_snapshotState(snapshot_state),.io_native_rawControlState(raw_state),
    .io_native_nativeControlBankState(bank_state),.io_native_endpointControlState(endpoint_view),
    .io_descriptorEntry(descriptor_entry),.io_descriptorValid(descriptor_entry==0),
    .io_descriptorBank(8'd1),.io_descriptorSlot(16'd0),.io_descriptorWidth(16'd64),.io_descriptorDepth(32'd1),
    .io_bankRequestValid(bank_request_valid),.io_bankRequestReady(bank_request_ready),
    .io_bank(bank),.io_slot(slot),.io_address(address),.io_bankResponseValid(bank_response_valid),
    .io_bankResponseReady(bank_response_ready),.io_bankResponseData(bank_response_data),.io_bankResponseError(1'b0),
    .io_endpointState(endpoint_state));
`define NT dut.nativeTransport
`define NC dut.nativeTransport.native_capture
`define TR dut.nativeTransport.transport
  wire [282:0] original_owner={`NC.error,`NC.phase,`NC.physical.error,`NC.physical.cut_cycle,
    `NC.physical.captured_ce,`NC.physical.release_pending,`NC.physical.sampled,`NC.physical.freeze_low,
    `NC.snapshot.error,`NC.snapshot.cut_cycle,`NC.snapshot.occupied,`NC.snapshot.payload};
  wire [410:0] original_coordinator={`TR.cut.error,`TR.cut.cut_cycle,`TR.cut.state,
    `TR.address,`TR.descriptor_entry,`TR.mmio_response_error,`TR.mmio_rdata,`TR.mmio_response_valid,
    `TR.transport_error,`TR.outstanding,`TR.stream_crc,`TR.words,`TR.saved_data,`TR.saved_depth,
    `TR.saved_width,`TR.saved_slot,`TR.saved_bank,`TR.state};
  wire [65:0] original_payload_response={`NT.snapshot_response_error,`NT.snapshot_response_data,`NT.snapshot_response_valid};
  wire [66:0] original_bank={`NT.native_owner_bank.endpoint.failed,`NT.native_owner_bank.endpoint.pending,
    `NT.native_owner_bank.endpoint.saved_error,`NT.native_owner_bank.endpoint.saved_data};
  wire [826:0] original_view={original_bank,original_payload_response,original_owner,original_coordinator};
  // Canonical NASTI slots, independently reconstructed from original registers.
  wire [529:0] original_adapter={dut.adapter.errorReadRemaining,{60'b0,dut.adapter.responseId},
    dut.adapter.responseData,dut.adapter.responseError,dut.adapter.responseValid,dut.adapter.writing,
    dut.adapter.busy,dut.adapter.badW,dut.adapter.haveAR,dut.adapter.haveW,dut.adapter.haveAW,
    dut.adapter.ar_user,{60'b0,dut.adapter.ar_id},dut.adapter.ar_region,dut.adapter.ar_qos,
    dut.adapter.ar_prot,dut.adapter.ar_cache,dut.adapter.ar_lock,dut.adapter.ar_burst,dut.adapter.ar_size,
    dut.adapter.ar_len,{32'b0,dut.adapter.ar_addr},dut.adapter.wd_user,dut.adapter.wd_strb,
    {60'b0,dut.adapter.wd_id},dut.adapter.wd_last,dut.adapter.wd_data,dut.adapter.aw_user,
    {60'b0,dut.adapter.aw_id},dut.adapter.aw_region,dut.adapter.aw_qos,dut.adapter.aw_prot,
    dut.adapter.aw_cache,dut.adapter.aw_lock,dut.adapter.aw_burst,dut.adapter.aw_size,
    dut.adapter.aw_len,{32'b0,dut.adapter.aw_addr}};
  wire [757:0] original_endpoint={original_adapter,dut.localError,dut.localData,dut.localValid,
    dut.counterOverflow,dut.hostDrainedFrames,dut.producedSnapshot,dut.producedFrames,dut.invalid};
  integer checks=0,raw_edges=0,frames=0,words=0,requests=0,stalls=0,control_acks=0,shadow_captures=0;
  integer fd=0,shadow_fd=0,cuts=0,layout_planes=0;
  reg [129:0] expected_payload=0;
  reg [319:0] padded_owner=0;
  reg [191:0] padded_payload=0;
  reg [63:0] expected_cycle=0;
  reg [1584:0] expected_shadow=0;
  reg [1599:0] padded_shadow=0;
  reg was_valid=0,expect_fault=0;
  reg [511:0] held_frame=0;
  reg held_valid=0;
  string scenario,path;
  task check(input bit ok,input string signal_name);
    checks++;
    if(!ok)begin
      $display("NATIVE_ENDPOINT_DIVERGENCE signal=%s raw_time=%0t raw_phase=%0d target_cycle=%0d cut=%0d frames=%0d words=%0d requests=%0d control_acks=%0d shadow_captures=%0d",
        signal_name,$time,`NC.phase,target_cycle,native_cut_cycle,frames,words,requests,control_acks,shadow_captures);
      $dumpflush;checkpoint_widget_failed();$finish;
    end
  endtask
  task tick;@(posedge clock);#2;endtask
  task write_mmio(input [7:0] addr,input [31:0] data,input bit error_expected=0);
    bit a,w;integer n;
    @(negedge clock);#1;awvalid=1;wvalid=1;awaddr=addr;wdata=data;bready=0;a=0;w=0;
    for(n=0;n<200;n++)begin
      #1;if(awvalid&&awready)a=1;if(wvalid&&wready)w=1;
      tick();@(negedge clock);#1;if(a)awvalid=0;if(w)wvalid=0;if(a&&w)break;
    end
    check(a&&w,"NASTI_AW_W_accepted");
    for(n=0;n<200;n++)begin #1;if(bvalid)break;tick();@(negedge clock);#1;end
    check(bvalid&&bid==3&&bresp==(error_expected?2:0),"NASTI_write_response");
    repeat(2)begin tick();check(bvalid&&bid==3&&bresp==(error_expected?2:0),"NASTI_B_backpressure");end
    @(negedge clock);#1;bready=1;tick();@(negedge clock);#1;bready=0;
  endtask
  reg [31:0] last_read;
  task read_mmio(input [7:0] addr);
    bit a;integer n;reg [31:0] saved;
    @(negedge clock);#1;arvalid=1;araddr=addr;rready=0;a=0;
    for(n=0;n<200;n++)begin
      #1;if(arvalid&&arready)a=1;tick();@(negedge clock);#1;if(a)begin arvalid=0;break;end
    end
    check(a,"NASTI_AR_accepted");
    for(n=0;n<200;n++)begin #1;if(rvalid)break;tick();@(negedge clock);#1;end
    check(rvalid&&rid==7&&rlast&&rresp==0,"NASTI_read_response");last_read=rdata;saved=rdata;
    repeat(2)begin tick();check(rvalid&&rid==7&&rlast&&rresp==0&&rdata===saved,"NASTI_R_backpressure");end
    @(negedge clock);#1;rready=1;tick();@(negedge clock);#1;rready=0;
  endtask
  task common_reset;
    @(negedge clock);#1;reset=1;owner_fault=0;expect_fault=0;
    repeat(4)tick();@(negedge clock);#1;reset=0;tick();
    check(bank_state==0&&!native_failed&&!freeze&&!dut.invalid,"common_reset_all_owners");
    read_mmio(8'h60);write_mmio(8'h7c,0);
    check(!$isunknown(original_endpoint),"frontdoor_initializes_original_endpoint_after_reset");
  endtask
  task begin_capture(input string filename);
    frames=0;words=0;requests=0;control_acks=0;
    fd=$fopen(filename,"w");check(fd!=0,"open_frames");write_mmio(0,1);
  endtask
  task finish_capture;
    while(frames<TOTAL_FRAMES)tick();
    check(words==9&&requests==1&&control_acks==5,"complete_native_descriptor_words");
    $fclose(fd);fd=0;write_mmio(0,2);while(freeze)tick();
  endtask
  always @(posedge clock)begin
    if(reset)begin bank_response_valid<=0;raw_edges=0;live_state<=0;was_valid=0;held_valid=0;end
    else begin
      raw_edges++;
      // Raw-clock reader noise is not a capture oracle. Staging must preserve
      // every preedge bit even while this independent source keeps advancing.
      for(integer b=0;b<BITS;b++)live_state[b]<=((b+raw_edges)%13)<6;
      if(bank_response_valid&&bank_response_ready)bank_response_valid<=0;
      if(bank_request_valid&&bank_request_ready)begin
        check(bank==1&&slot==0&&address==0,"original_bank_selector");bank_response_valid<=1;requests++;
      end
      if(`NC.phase==2)begin expected_payload=live_state;expected_cycle=target_cycle;end
      if(native_valid&&!was_valid)begin
        padded_owner=0;padded_owner[282:0]={6'b0,3'd3,3'b0,expected_cycle,ce,1'b0,1'b1,1'b1,
          6'b0,expected_cycle,1'b1,expected_payload};
        padded_payload=0;padded_payload[129:0]=expected_payload;
      end
      was_valid=native_valid;
      check(raw_state==={original_payload_response,original_coordinator,original_owner},"complete_raw_owner_readout");
      check(bank_state===original_bank,"separate_67_original_bank_bits");
      if(native_valid)begin
        check(endpoint_view===original_view,"endpoint_coordinator_layout");
        check(original_owner===padded_owner[282:0]&&snapshot_state===expected_payload,"whole_staged_owner");
      end
      check(endpoint_state===original_endpoint,"complete_original_endpoint_state");
      if(!expect_fault)check(!native_failed&&!bank_state[66],"healthy_native_permission");
      if(dut.snapshot.io_access&&dut.snapshot.io_write&&dut.snapshot.io_address==8'h78&&
          dut.snapshot.io_data==1&&!dut.snapshot.io_error)begin
        check(!$isunknown({original_endpoint,original_view}),"shadow_originals_fully_binary_before_capture");
        expected_shadow={original_endpoint,original_view};shadow_captures++;
        check(native_valid&&native_cut_cycle==target_cycle,"shadow_uses_actual_coordinator_cut");
      end
      if(`NT.control_response_valid&&`NT.response_ready&&`NT.control_selected)control_acks++;
      if(stream_valid&&!stream_ready)stalls++;
      if(held_valid&&!stream_abort)check(stream_valid&&stream_data===held_frame,"DMA_backpressure_stability");
      held_valid=stream_valid&&!stream_ready;held_frame=stream_data;
      if(stream_valid&&stream_ready)begin
        check(!$isunknown(stream_data),"DMA_frame_fully_binary");
        check(!stream_abort&&freeze&&stream_data[159:96]==expected_cycle,"DMA_common_cut_permission");
        if(frames==0)check(stream_data[95:80]==1&&stream_data[255:224]==4&&stream_data[511:256]==HASH,"manifest_header");
        else if(stream_data[95:80]==2)begin
          check(stream_data[223:160]==words&&!stream_last,"ordered_word_sequence");
          if(words==0)check(stream_data[399:336]===bank_response_data,"external_bank_word");
          else if(words<=CONTROL_WORDS)check(stream_data[399:336]===padded_owner[(words-1)*64+:64],"native_owner_bank_word");
          else check(stream_data[399:336]===padded_payload[(words-1-CONTROL_WORDS)*64+:64],"native_payload_word");
          words++;
        end else check(stream_last&&words==9,"complete_trailer");
        check(fd!=0,"frame_log_owned");$fdisplay(fd,"%0128h",stream_data);frames++;
      end
    end
  end
  always @(negedge clock)begin
    #1;
    // Diagnose a settled mapping fault before the next accepting raw edge,
    // including when the old ready value would otherwise permit a DMA beat.
    // This is a component pre-ack check, not CPU target-edge acceptance.
    if(!reset)begin
      if(native_valid)check(endpoint_view===original_view,"endpoint_coordinator_layout");
      check(bank_state===original_bank,"separate_67_original_bank_bits_preedge");
      check(endpoint_state===original_endpoint,"complete_original_endpoint_state_preedge");
    end
    stream_ready=scenario!="abort"&&(raw_edges%5==0||raw_edges%5==3);
  end
  initial begin
    $dumpfile("native-widget-endpoint.vcd");$dumpvars(0,native_widget_endpoint_tb);
    if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
    // Literal endpoint order, independently written here rather than the
    // Scala helper or its inverse. Exercise every raw and separate-bank bit.
    for(integer plane=0;plane<827;plane++)begin
      probe_raw=0;probe_bank=0;
      if(plane<760)probe_raw[plane]=1;else probe_bank[plane-760]=1;
      #1;
      check(!$isunknown({probe_view,probe_recovered_raw,probe_recovered_bank}),"layout_plane_binary");
      check(probe_view===literal_probe_view,"literal_coordinator_first_one_hot_plane");
      check(probe_recovered_raw===probe_raw&&probe_recovered_bank===probe_bank,"layout_plane_exact_inverse");
      check(probe_correct_high&&!probe_misleading_low&&!probe_acknowledged,"conflicting_high_low_coordinator_certificates");
      layout_planes++;
    end
    probe_raw=0;probe_bank=0;
    $display("NATIVE_ENDPOINT_LAYOUT_PASS planes=827 raw_bits=760 separate_bank_bits=67 correct_high=1 misleading_low=0");
    repeat(4)tick();@(negedge clock);#1;reset=0;
    // Initialize the existing unreset AR/AW/W and response/local data registers
    // solely through the NASTI interface before admitting a complete shadow.
    read_mmio(8'h60);write_mmio(8'h7c,0);
    check(!$isunknown(original_endpoint),"frontdoor_initializes_original_endpoint");
    if(scenario=="lost-owner")begin
      begin_capture("lost-owner.frames");
      while(!bank_state[65])begin @(negedge clock);#2;end
      expect_fault=1;owner_fault=1;#1;
      check(!native_valid&&!`NT.control_response_valid&&stream_abort,"owner_loss_revokes_before_ack");
      repeat(4)tick();
      check(bank_state[66:65]==3&&native_failed&&freeze&&control_acks==0&&words==1,"lost_owner_pending_no_ack");
      $fclose(fd);fd=0;common_reset();begin_capture("recovery.frames");finish_capture();
      $display("NATIVE_ENDPOINT_OWNER_LOSS_PASS control_acks_before_reset=0 recovery_frames=11");$finish;
    end
    if(scenario=="abort")begin
      begin_capture("abort.frames");while(!stream_valid)tick();
      check(native_valid&&freeze&&frames==0,"abort_holds_unpublished_header");
      write_mmio(0,4);while(freeze)tick();
      check(frames==0&&requests==0&&dut.invalid&&!native_failed,"frontdoor_abort_discards_unpublished_stream");
      write_mmio(0,1,1);$fclose(fd);fd=0;common_reset();scenario="recovery";
      begin_capture("recovery.frames");finish_capture();
      $display("NATIVE_ENDPOINT_ABORT_PASS published_frames=0 blocked_restart=1 recovery_frames=11");$finish;
    end
    for(integer cut=0;cut<4;cut++)begin
      repeat(19+cut*11)tick();path=$sformatf("cut%0d.frames",cut);begin_capture(path);
      while(frames<TOTAL_FRAMES)tick();
      // Transport remains frozen after its trailer until frontdoor publish.
      // The native bank's saved word is now nonzero and separately observable.
      check(bank_state[63:0]!=0&&native_valid,"separate_bank_live_word_nonzero");
      write_mmio(8'h78,1);
      check(shadow_captures==cut+1,"frontdoor_shadow_capture_acknowledged");
      padded_shadow=0;padded_shadow[1584:0]=expected_shadow;
      read_mmio(8'h94);check(last_read==25,"shadow_word_count");
      read_mmio(8'h9c);check(last_read==1585,"shadow_bit_count");
      read_mmio(8'h8c);check(last_read==expected_cycle[31:0],"shadow_cut_low");
      read_mmio(8'h90);check(last_read==expected_cycle[63:32],"shadow_cut_high");
      path=$sformatf("cut%0d.shadow",cut);shadow_fd=$fopen(path,"w");check(shadow_fd!=0,"open_shadow");
      for(integer word_index=0;word_index<SHADOW_WORDS;word_index++)begin
        write_mmio(8'h7c,word_index);read_mmio(8'h80);
        check(last_read===padded_shadow[word_index*64+:32],"frontdoor_shadow_low_every_word");
        $fwrite(shadow_fd,"%08h ",last_read);read_mmio(8'h84);
        check(last_read===padded_shadow[word_index*64+32+:32],"frontdoor_shadow_high_every_word");
        $fdisplay(shadow_fd,"%08h",last_read);
      end
      $fclose(shadow_fd);write_mmio(8'h78,2);finish_capture();cuts++;
    end
    check(cuts==4&&stalls>0&&shadow_captures==4,"four_progressing_captures_with_backpressure");
    $display("NATIVE_ENDPOINT_PASS cuts=4 frames_per_cut=11 shadow_bits=1585 shadow_words=25 separate_bank_bits=67 checks=%0d stalls=%0d",checks,stalls);$finish;
  end
  initial begin #5000000;check(0,"watchdog");end
endmodule
