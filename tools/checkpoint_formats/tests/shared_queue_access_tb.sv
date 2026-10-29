`timescale 1ns/1ps
// Software queue/RAM oracle, including write-first synchronous address latches.
module shared_queue_access_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0; always #5 clock=~clock;
  reg reset=1, endpoint_reset=1;
  reg [2:0] enq_valid=0, deq_ready=0;
  reg [129:0] enq_bits[0:2];
  wire [2:0] enq_ready,deq_valid;
  wire [129:0] deq_bits[0:2];
  wire [2:0] count[0:2];
  reg [1:0] freeze=0, request_valid=0,response_ready=0;
  reg [7:0] bank[0:1]; reg [15:0] slot[0:1]; reg [31:0] word_address[0:1];
  wire [1:0] request_ready,response_valid,response_error;
  wire [63:0] response_data[0:1];
  SharedQueueSynthesisTop dut(.clock(clock),.reset(reset),
    .lane0_enq_valid(enq_valid[0]),
    .lane0_enq_bits(enq_bits[0]),
    .lane0_deq_ready(deq_ready[0]),
    .lane0_enq_ready(enq_ready[0]),
    .lane0_deq_valid(deq_valid[0]),
    .lane0_deq_bits(deq_bits[0]),
    .lane0_count(count[0]),
    .lane1_enq_valid(enq_valid[1]),
    .lane1_enq_bits(enq_bits[1]),
    .lane1_deq_ready(deq_ready[1]),
    .lane1_enq_ready(enq_ready[1]),
    .lane1_deq_valid(deq_valid[1]),
    .lane1_deq_bits(deq_bits[1]),
    .lane1_count(count[1]),
    .lane2_enq_valid(enq_valid[2]),
    .lane2_enq_bits(enq_bits[2]),
    .lane2_deq_ready(deq_ready[2]),
    .lane2_enq_ready(enq_ready[2]),
    .lane2_deq_valid(deq_valid[2]),
    .lane2_deq_bits(deq_bits[2]),
    .lane2_count(count[2]),
    .checkpoint_shell_region0_ckpt_reset(endpoint_reset),
    .checkpoint_shell_region0_ckpt_freeze(freeze[0]),
    .checkpoint_shell_region0_ckpt_req_valid(request_valid[0]),
    .checkpoint_shell_region0_ckpt_req_ready(request_ready[0]),
    .checkpoint_shell_region0_ckpt_bank(bank[0]),
    .checkpoint_shell_region0_ckpt_slot(slot[0]),
    .checkpoint_shell_region0_ckpt_address(word_address[0]),
    .checkpoint_shell_region0_ckpt_resp_valid(response_valid[0]),
    .checkpoint_shell_region0_ckpt_resp_ready(response_ready[0]),
    .checkpoint_shell_region0_ckpt_resp_data(response_data[0]),
    .checkpoint_shell_region0_ckpt_resp_error(response_error[0]),
    .checkpoint_shell_region1_ckpt_reset(endpoint_reset),
    .checkpoint_shell_region1_ckpt_freeze(freeze[1]),
    .checkpoint_shell_region1_ckpt_req_valid(request_valid[1]),
    .checkpoint_shell_region1_ckpt_req_ready(request_ready[1]),
    .checkpoint_shell_region1_ckpt_bank(bank[1]),
    .checkpoint_shell_region1_ckpt_slot(slot[1]),
    .checkpoint_shell_region1_ckpt_address(word_address[1]),
    .checkpoint_shell_region1_ckpt_resp_valid(response_valid[1]),
    .checkpoint_shell_region1_ckpt_resp_ready(response_ready[1]),
    .checkpoint_shell_region1_ckpt_resp_data(response_data[1]),
    .checkpoint_shell_region1_ckpt_resp_error(response_error[1]));
  wire [129:0] debug_q0_ram0=dut.host.q0.ram[0];
  wire [129:0] debug_q0_ram1=dut.host.q0.ram[1];
  wire [129:0] debug_q0_ram2=dut.host.q0.ram[2];
  wire [129:0] debug_q0_ram3=dut.host.q0.ram[3];
  wire [129:0] debug_q0_ram4=dut.host.q0.ram[4];
  wire [129:0] debug_q0_ram5=dut.host.q0.ram[5];
  wire [129:0] debug_q1_ram0=dut.host.q1.ram[0];
  wire [129:0] debug_q1_ram1=dut.host.q1.ram[1];
  wire [129:0] debug_q1_ram2=dut.host.q1.ram[2];
  wire [129:0] debug_q1_ram3=dut.host.q1.ram[3];
  wire [129:0] debug_q1_ram4=dut.host.q1.ram[4];
  wire [129:0] debug_q1_ram5=dut.host.q1.ram[5];
  wire [129:0] debug_q2_ram0=dut.host.q2.ram[0];
  wire [129:0] debug_q2_ram1=dut.host.q2.ram[1];
  wire [129:0] debug_q2_ram2=dut.host.q2.ram[2];
  wire [129:0] debug_q2_ram3=dut.host.q2.ram[3];
  wire [129:0] debug_q2_ram4=dut.host.q2.ram[4];
  wire [129:0] debug_q2_ram5=dut.host.q2.ram[5];
  reg [129:0] memory[0:2][0:5];
  integer wp[0:2],rp[0:2],ra[0:2],occupancy[0:2];
  bit full[0:2];
  bit initialized=0, armed=0;
  integer checks=0,reads=0,stalls=0,cuts=0,edges=0,selected_edges=0;
  integer pushes[0:2],pops[0:2],wraps[0:2],same_address_writes[0:2];
  integer collision_before=0;
  integer response_wait_cycles=0,delayed_reads=0,cancellations=0,held_response_releases=0,premature_releases=0,running_reset_pulses=0;
  reg [63:0] expected_word=0;
  integer expected_queue=0;
  task check(input bit ok,input string why);
    checks++;
    if(!ok) begin
      $display("SHARED_QUEUE_DIVERGENCE signal=%s cuts=%0d edges=%0d frozen=%b response_ack=%b reads=%0d queue=%0d bank=%0d slot=%0d address=%0d actual=%h expected=%h",why,cuts,edges,freeze,response_ready,reads,expected_queue,bank[expected_queue],slot[expected_queue],word_address[expected_queue],response_data[expected_queue],expected_word);
      checkpoint_widget_failed();$finish;
    end
  endtask
  always @(posedge clock) begin : model
    bit take_in,take_out; integer next_read;
    edges++;
    for(integer q=0;q<3;q++) begin
      if(q==2 || !freeze[q]) begin
        if(q<2) selected_edges++;
        take_in=enq_valid[q] && !(wp[q]==rp[q] && full[q]);
        take_out=deq_ready[q] && !(wp[q]==rp[q] && !full[q]);
        next_read=take_out ? (rp[q]==5?0:rp[q]+1):rp[q];
        ra[q]=next_read;
        if(take_in) begin
          if(wp[q]==next_read)same_address_writes[q]++;
          memory[q][wp[q]]=enq_bits[q];pushes[q]++;if(wp[q]==5)wraps[q]++;
        end
        if(take_out)pops[q]++;
        if(reset)begin wp[q]=0;rp[q]=0;full[q]=0;end
        else begin
          if(take_in)wp[q]=(wp[q]==5?0:wp[q]+1);
          if(take_out)rp[q]=next_read;
          if(take_in!=take_out)full[q]=take_in;
        end
      end
      occupancy[q]=wp[q]==rp[q] ? (full[q]?6:0) : (wp[q]>rp[q]?wp[q]-rp[q]:6+wp[q]-rp[q]);
    end
    #1;
    if(armed) for(integer q=0;q<3;q++) begin
      check(count[q]===3'(occupancy[q]),"public occupancy");
      check(enq_ready[q]===!(occupancy[q]==6),"public full backpressure");
      check(deq_valid[q]===!(occupancy[q]==0),"public empty backpressure");
      if(initialized)check(deq_bits[q]===memory[q][ra[q]],"public write-first synchronous memory");
    end
  end
  // Unselected execution keeps doing accepted RAM traffic during every capture.
  always @(negedge clock) if(initialized) begin
    #1; enq_valid[2]=1;deq_ready[2]=1;
    enq_bits[2]={2'(edges%4),64'h8badf00d01234567 ^ 64'(edges),64'(edges)*64'h123456789};
  end
  task readword(input integer q,input integer b,input integer s,input integer a,input reg[63:0] expected,input bit err);
    @(negedge clock);#2;
    bank[q]=b;slot[q]=s;word_address[q]=a;expected_word=expected;expected_queue=q;
    request_valid[q]=1;response_ready[q]=0;
    #1;check(request_ready[q],"independent endpoint request ready");
    @(posedge clock);#2;request_valid[q]=0;
    // The accepted selector must be retained across native RAM latency. Change
    // bank, slot, address and chunk before the delayed response is available.
    bank[q]=254;slot[q]=65535;word_address[q]=32'hffffffff;
    begin : response_wait
      integer latency;
      latency=0;
      while(!response_valid[q] && latency<12) begin
        check(!request_ready[q],"one outstanding request during synchronous memory latency");
        @(posedge clock);#2;latency++;response_wait_cycles++;
      end
      if(latency>0)delayed_reads++;
      check(response_valid[q],"bounded synchronous response latency");
    end
    check(response_valid[q] && response_error[q]===err,"response valid/error");
    check(response_data[q]===expected,"complete selected word");
    for(integer k=0;k<2+(reads%4);k++) begin
      @(negedge clock);#2;bank[q]=254;slot[q]=65535;word_address[q]=32'hffffffff;
      @(posedge clock);#2;stalls++;
      check(response_valid[q] && !request_ready[q] && response_data[q]===expected && response_error[q]===err,"backpressured original owner response");
    end
    @(negedge clock);#2;response_ready[q]=1;
    @(posedge clock);#2;response_ready[q]=0;reads++;
    check(!response_valid[q],"one response acknowledgement");
  endtask
  `include "shared-queue-selectors.svh"
  task active(input integer n,input integer seed);
    for(integer k=0;k<n;k++)begin
      @(negedge clock);#2;
      for(integer q=0;q<2;q++)begin
        enq_valid[q]=((k+seed+q*3)%7)!=0;
        deq_ready[q]=((k+seed+q*5)%5)<3;
        enq_bits[q]={2'((k+q)%4),64'hfedcba9876543210 ^ (64'(seed+k)*64'h234567),64'h123456789abcdef0 ^ 64'(k+q*100)};
      end
    end
  endtask
  task capture;
    integer sibling_before,sibling_pops_before,step_before;
    @(negedge clock);#2;freeze=3;
    step_before=selected_edges;sibling_before=pushes[2];sibling_pops_before=pops[2];
    allwords();
    check(pushes[2]>sibling_before+50 && pops[2]>sibling_pops_before+50,"unselected sibling accepts traffic outside reset during capture");
    readword(0,254,65535,0,0,1);readword(1,254,65535,0,0,1);
    // Reset must not consume frozen pointers or RAM reader address pipelines.
    @(negedge clock);#2;reset=1;
    repeat(2)@(posedge clock);
    #2;allwords();
    check(selected_edges==step_before,"zero functional edges during selected capture");
    check(pushes[2]>sibling_before+100,"unselected sibling retains accepted live RAM traffic");
    @(negedge clock);#2;reset=0;freeze=0;cuts++;
    active(45+cuts*7,17+cuts*13);
  endtask
  initial begin
    $dumpfile("shared-queue-access.vcd");$dumpvars(0,shared_queue_access_tb);
    for(integer q=0;q<3;q++)begin
      wp[q]=0;rp[q]=0;ra[q]=0;full[q]=0;pushes[q]=0;pops[q]=0;wraps[q]=0;same_address_writes[q]=0;enq_bits[q]=0;
    end
    for(integer q=0;q<2;q++)begin bank[q]=0;slot[q]=0;word_address[q]=0;end
    repeat(3)@(posedge clock);
    @(negedge clock);#2;reset=0;endpoint_reset=0;armed=1;
    // Initialize all RAM words through functional enqueue; full/empty get exercised.
    for(integer k=0;k<6;k++)begin
      @(negedge clock);#2;enq_valid=7;deq_ready=0;
      for(integer q=0;q<3;q++)enq_bits[q]={2'(q),64'(q*100+k),64'hf0e1d2c3b4a59687 ^ 64'(k)};
      @(posedge clock);#2;
    end
    @(negedge clock);#2;enq_valid=0;deq_ready=7;initialized=1;
    repeat(6)@(posedge clock);
    #2;active(61,3);
    repeat(4)capture();
    // Explicitly reject requests outside hold, and cancel a pending word on control reset.
    readword(0,0,0,0,0,1);
    // Cancel at borrowing, payload capture/re-prime, and completed response
    // phases. All paths must restore the original native reader
    // pipeline before release and must never resurrect the canceled response.
    for(integer phase=0;phase<3;phase++)begin
      @(negedge clock);#2;freeze=3;
      bank[0]=QUEUE0_RAM_BANK;slot[0]=QUEUE0_RAM_SLOT;word_address[0]=7;
      request_valid[0]=1;response_ready[0]=0;
      #1;check(request_ready[0],"cancel request ready");
      @(posedge clock);#2;request_valid[0]=0;
      bank[0]=254;slot[0]=65535;word_address[0]=32'hffffffff;
      if(phase<2)begin
        if(phase==1)begin @(posedge clock);#2;end
        check(!response_valid[0],"reset phase precedes memory response validity");
      end else begin : cancel_pending_wait
        integer latency;
        latency=0;
        while(!response_valid[0] && latency<12)begin @(posedge clock);#2;latency++;end
        check(response_valid[0],"pending response exists before reset");
      end
      @(negedge clock);#2;endpoint_reset=1;
      @(posedge clock);#2;check(!response_valid[0] && !response_valid[1],"control reset cancels in-flight and pending responses");
      repeat(4)begin @(posedge clock);#2;check(!response_valid[0] && !response_valid[1],"reset suppresses late response");end
      @(negedge clock);#2;endpoint_reset=0;
      repeat(4)begin @(posedge clock);#2;check(!response_valid[0] && !response_valid[1],"canceled request never resurrects");end
      check(request_ready[0],"endpoint recovers after cancel and memory re-prime");
      @(negedge clock);#2;freeze=0;cancellations++;
      active(9,103+phase);
    end
    // Release at both unfinished RAM phases. A response from a cut that was
    // broken before re-prime must be a retained zero/error, never stale data.
    for(integer phase=0;phase<2;phase++)begin
      @(negedge clock);#2;freeze=3;
      bank[0]=QUEUE0_RAM_BANK;slot[0]=QUEUE0_RAM_SLOT;word_address[0]=7;
      request_valid[0]=1;response_ready[0]=0;
      #1;check(request_ready[0],"premature release request ready");
      @(posedge clock);#2;request_valid[0]=0;
      bank[0]=254;slot[0]=65535;word_address[0]=32'hffffffff;
      if(phase==1)begin @(posedge clock);#2;end
      check(!response_valid[0],"premature release precedes valid response");
      @(negedge clock);#2;freeze=0;
      begin : premature_release_wait
        integer latency;
        latency=0;
        while(!response_valid[0] && latency<12)begin @(posedge clock);#2;latency++;end
        check(response_valid[0] && response_error[0] && response_data[0]===64'b0,"broken cut rejects stale native memory payload");
      end
      repeat(3)begin
        @(posedge clock);#2;
        check(response_valid[0] && !request_ready[0] && response_error[0] && response_data[0]===64'b0,"premature release retains zero/error under backpressure");
      end
      @(negedge clock);#2;response_ready[0]=1;
      @(posedge clock);#2;response_ready[0]=0;reads++;premature_releases++;
      check(!response_valid[0],"premature release error acknowledged once");
      active(7,117+phase);
    end
    // Releasing functional execution while a response is held must preserve
    // the accepted payload and restore the original synchronous reader on the
    // very first resumed edge, including same-address RAM writes/reads.
    // Empty q0 so a single enqueue writes its currently addressed RAM word.
    @(negedge clock);#2;enq_valid[0]=0;deq_ready[0]=1;
    repeat(6)begin @(posedge clock);#2;end
    check(occupancy[0]==0 && wp[0]==rp[0],"directed pre-release empty queue");
    collision_before=same_address_writes[0];
    @(negedge clock);#2;enq_valid[0]=1;deq_ready[0]=0;
    enq_bits[0]={2'b11,64'hb8b7b6b5b4b3b2b1,64'ha8a7a6a5a4a3a2a1};
    @(posedge clock);#2;
    check(same_address_writes[0]==collision_before+1,"write-first collision immediately before freeze");
    @(negedge clock);#2;freeze=3;
    expected_word=64'(memory[0][2] >> 64);expected_queue=0;
    bank[0]=QUEUE0_RAM_BANK;slot[0]=QUEUE0_RAM_SLOT;word_address[0]=7;
    request_valid[0]=1;response_ready[0]=0;
    #1;check(request_ready[0],"held release request ready");
    @(posedge clock);#2;request_valid[0]=0;
    bank[0]=254;slot[0]=65535;word_address[0]=32'hffffffff;
    begin : held_release_wait
      integer latency;
      latency=0;
      while(!response_valid[0] && latency<12)begin @(posedge clock);#2;latency++;end
      check(response_valid[0] && !response_error[0] && response_data[0]===expected_word,"held release complete accepted word");
    end
    collision_before=same_address_writes[0];
    @(negedge clock);#2;freeze=0;enq_valid[0]=1;deq_ready[0]=1;
    enq_bits[0]={2'b10,64'hc8c7c6c5c4c3c2c1,64'hd8d7d6d5d4d3d2d1};
    for(integer k=0;k<9;k++)begin
      @(posedge clock);#2;
      if(k==0)check(same_address_writes[0]==collision_before+1,"write-first collision on first resumed edge");
      check(response_valid[0] && !request_ready[0] && !response_error[0] && response_data[0]===expected_word,"release preserves response while original execution resumes");
    end
    @(negedge clock);#2;response_ready[0]=1;
    @(posedge clock);#2;response_ready[0]=0;reads++;held_response_releases++;
    check(!response_valid[0],"released response acknowledged once");
    active(129,97);
    // Endpoint reset has no authority over running functional queue owners.
    // Keep traffic and the public-output oracle active throughout the pulse.
    @(negedge clock);#2;endpoint_reset=1;enq_valid[1:0]=3;deq_ready[1:0]=3;
    active(11,149);
    @(posedge clock);#2;
    check(!response_valid[0] && !response_valid[1] && !request_ready[0] && !request_ready[1],"running endpoint reset suppresses transport only");
    @(negedge clock);#2;endpoint_reset=0;running_reset_pulses++;
    active(17,167);
    check(running_reset_pulses==1,"running endpoint reset pulse coverage");
    check(cuts==4 && reads==364,"original 361 reads plus held and premature release transfers");
    check(delayed_reads>=288 && response_wait_cycles>=delayed_reads && cancellations==3 && held_response_releases==1 && premature_releases==2,"synchronous RAM latency and all three reset cancellation phases");
    for(integer q=0;q<3;q++)check(pushes[q]>50 && pops[q]>50 && wraps[q]>8,"live enqueue/dequeue/pointer wrapping coverage");
    $display("SHARED_QUEUE_PASS checks=%0d reads=%0d stalls=%0d edges=%0d cuts=%0d sibling_pushes=%0d delayed_reads=%0d wait_cycles=%0d cancellations=%0d held_releases=%0d premature_releases=%0d running_reset_pulses=%0d",checks,reads,stalls,edges,cuts,pushes[2],delayed_reads,response_wait_cycles,cancellations,held_response_releases,premature_releases,running_reset_pulses);
    $finish;
  end
  initial begin #2000000;check(0,"watchdog");end
endmodule
