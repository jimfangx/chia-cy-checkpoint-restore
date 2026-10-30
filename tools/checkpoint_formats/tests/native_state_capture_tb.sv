`timescale 1ns/1ps
`ifndef CAPTURE_BITS
`define CAPTURE_BITS 1036
`endif
module native_state_capture_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer BITS=`CAPTURE_BITS, WORDS=(BITS+63)/64;
  reg clock=0; always #5 clock=~clock;
  reg reset=1,capture_request=0,release_request=0;
  reg [2:0] ce_corruption=0;
  wire [2:0] ce;
  reg [1:0] owner_present=3,owner_error=0;
  reg ack=1,reader_idle=1,borrow_attempt=0;
  wire hold,root_clock,mask,valid,borrow,failed,ready,word_error;
  wire [2:0] gate_clock,captured_ce,phase;
  wire [5:0] error;
  wire [63:0] word_data,cut_cycle;
  wire [BITS-1:0] payload;
  wire [BITS+152:0] control_state;
  reg [63:0] target_cycle=0;
  assign ce=reset ? 3'b111 :
    ({target_cycle[1]^target_cycle[0],target_cycle[2],!target_cycle[0]} ^ ce_corruption);
  reg [63:0] cycle_offset=0;
  reg [BITS-1:0] live_state=0,expected;
  reg [WORDS*64-1:0] padded;
  reg [31:0] address=0;
  reg [63:0] functional[0:2];
  reg [63:0] expected_functional[0:2];
  wire [63:0] debug_functional0=functional[0],debug_functional1=functional[1],debug_functional2=functional[2];
  reg [63:0] expected_target_cycle=0;
  bit oracle_armed=0;
  integer checks=0,cuts=0,reads=0,borrows=0,root_edges=0;
  string test_case="healthy";
  CheckpointNativeStateCapture #(.BITS(BITS),.GATES(3),.OWNERS(2)) dut(
    .clock(clock),.reset(reset),.capture_request(capture_request),.release_request(release_request),
    .capture_ready(ready),.ce(ce),.target_cycle(target_cycle+cycle_offset),
    .owner_present(owner_present),.owner_frozen({2{hold && ack}}),.owner_error(owner_error),
    .reader_idle(reader_idle),.borrow_attempt(borrow_attempt),.live_state(live_state),.word_address(address),
    .root_clock(root_clock),.gate_clock(gate_clock),.clock_mask(mask),.functional_hold(hold),
    .valid(valid),.borrow_enable(borrow),.failed(failed),.word_data(word_data),.cut_cycle(cut_cycle),
    .word_error(word_error),.snapshot_state(payload),.captured_ce(captured_ce),.phase(phase),.error(error),
    .control_state(control_state));
  always @(posedge root_clock) begin
    root_edges++;
    if(reset)target_cycle<=0;else target_cycle<=target_cycle+1;
  end
  generate for(genvar g=0;g<3;g++)begin
    always @(posedge gate_clock[g])if(reset)functional[g]<=0;else functional[g]<=functional[g]+g+1;
  end endgenerate
  // A raw reader vector can change while original owners are held. No test
  // initialization or comparison reads/writes any internal DUT register.
  always @(posedge clock)begin
    for(integer b=0;b<BITS;b++)live_state[b]<=((target_cycle+b*17+checks)%7)<3;
    if(borrow_attempt && borrow)borrows++;
    // Independent software enable/edge oracle; it never follows the generated
    // gate outputs. Compare every raw edge, including freeze and release.
    if(reset)begin
      expected_target_cycle=0;
      for(integer g=0;g<3;g++)expected_functional[g]=0;
    end else if(!mask)begin
      expected_target_cycle++;
      for(integer g=0;g<3;g++)if(ce[g])expected_functional[g]+=g+1;
    end
    #1;
    // Vendor glbl holds the native gates in startup for 100 ns. Arm only after
    // real gated reset edges and explicit complete reset-state readback, then
    // compare every raw edge before any capture or borrowed traffic.
    if(oracle_armed)begin
      check(target_cycle===expected_target_cycle,"every original target edge against independent enable oracle");
      for(integer g=0;g<3;g++)
        check(functional[g]===expected_functional[g],"every original gated owner against independent enable oracle");
    end
  end
  task check(input bit ok,input string signal_name);
    checks++;
    if(!ok)begin
      $display("NATIVE_CAPTURE_DIVERGENCE case=%s signal=%s cut=%0d phase=%0d target_cycle=%0d borrows=%0d reads=%0d",test_case,signal_name,cuts,phase,target_cycle,borrows,reads);
      checkpoint_widget_failed();$finish;
    end
  endtask
  // Retain the original hierarchical policy as an independent differential
  // oracle while exercising every phase and directed command/owner fault.
  // Check both half cycles: a newly arriving fault must revoke before an edge,
  // without adding permission registers or changing the checkpoint state ABI.
  always @(posedge clock or negedge clock) begin
    #1;
    if(oracle_armed)begin
      check(failed === (|dut.error || |dut.faults || phase==6),
            "factored failure matches complete hierarchical fault policy");
      check(valid === (dut.read_safe && !dut.faults[3]),
            "factored validity matches complete hierarchical fault policy");
      check(borrow === (valid && dut.snapshot_borrow),
            "factored borrow matches original snapshot permission");
    end
  end
  task tick;
    @(posedge clock);#2;
  endtask
  task start_cut;
    @(negedge clock);#2;check(ready,"capture ready");capture_request=1;
    tick();capture_request=0;
    check(hold && !valid && !borrow,"hold precedes snapshot permission");
    repeat(4)begin tick();check(!valid && !borrow,"wait for delayed frozen owners and idle readers");end
    @(negedge clock);#2;ack=1;reader_idle=1;
    while(phase!=2)begin tick();check(!failed,"healthy wait");end
    if(test_case=="sample-busy" || test_case=="sample-owner" || test_case=="sample-borrow" ||
       test_case=="sample-capture" || test_case=="sample-release")begin
      // Withdraw a prerequisite after WAIT_CUT, before the actual atomic edge.
      @(negedge clock);#2;
      if(test_case=="sample-busy")reader_idle=0;
      else if(test_case=="sample-owner")owner_present=1;
      else if(test_case=="sample-capture")capture_request=1;
      else if(test_case=="sample-release")release_request=1;
      else borrow_attempt=1;
      #1;check(failed && !valid && !borrow,"unsafe sampling edge revokes before acknowledgement");
      tick();borrow_attempt=0;capture_request=0;release_request=0;
      check(payload===0 && cut_cycle==0,"rejected sampling edge retains the entire previous snapshot");
      repeat(8)begin tick();check(hold && mask && phase==6 && failed,"rejected atomic sample remains parked");end
      $display("NATIVE_CAPTURE_NEGATIVE_PASS case=%s bits=%0d borrows=%0d reads=%0d",test_case,BITS,borrows,reads);$finish;
    end
    @(posedge clock);expected=live_state;
    #2;check(valid && borrow && payload===expected,"every native bit at first preedge snapshot");
    check(cut_cycle==target_cycle && captured_ce==ce,"common physical and snapshot cut labels");
    $display("NATIVE_CAPTURE_CUT ordinal=%0d target_cycle=%0d bits=%0d",cuts,cut_cycle,BITS);
    padded=0;padded[BITS-1:0]=expected;
    cuts++;
  endtask
  task negative;
    @(negedge clock);#2;
    case(test_case)
      "owner":owner_present=1;
      "owner-error":owner_error=2;
      "freeze":ack=0;
      "ce":ce_corruption=1;
      "cycle":cycle_offset=1;
      "overlap":capture_request=1;
      "borrow":begin release_request=1;borrow_attempt=1;end
      default:check(0,"unknown negative");
    endcase
    #1;check(failed && !valid && !borrow && word_error && word_data==0,"fault revokes before edge acknowledgement");
    tick();capture_request=0;release_request=0;borrow_attempt=0;
    // Dropping all host commands cannot reopen a faulted cut.
    begin: stopped
      integer before_edges;before_edges=root_edges;
      repeat(8)begin tick();check(hold && mask && failed && phase==6,"sticky fault parks all owners");end
      check(root_edges==before_edges,"no acknowledged functional edge after fault");
    end
    $display("NATIVE_CAPTURE_NEGATIVE_PASS case=%s bits=%0d borrows=%0d reads=%0d",test_case,BITS,borrows,reads);
    $finish;
  endtask
  initial begin
    if($value$plusargs("CASE=%s",test_case))begin end
    $dumpfile("native-state-capture.vcd");$dumpvars(0,native_state_capture_tb);
    repeat(16)tick();@(negedge clock);#2;
    check(functional[0]===0 && functional[1]===0 && functional[2]===0 && target_cycle===0,
          "complete original reset state after real vendor-clock reset edges");
    oracle_armed=1;reset=0;
    repeat(8)tick();
    if(test_case=="early-release" || test_case=="early-borrow" || test_case=="early-owner")begin
      @(negedge clock);#2;
      if(test_case=="early-release")release_request=1;
      else if(test_case=="early-borrow")borrow_attempt=1;
      else begin
        owner_present=1;
        #1;check(!ready && !failed,"missing idle owner refuses readiness independently of command");
        capture_request=ready;
        tick();check(phase==0 && !ready && !failed,"ready-qualified producer remains stable while owner is absent");
        @(negedge clock);#2;capture_request=1;
      end
      #1;check(failed && !valid && !borrow,"invalid running command revokes grant");
      tick();release_request=0;borrow_attempt=0;capture_request=0;
      repeat(6)tick();check(hold && mask && failed,"invalid running command fail stop");
      $display("NATIVE_CAPTURE_NEGATIVE_PASS case=%s bits=%0d borrows=%0d reads=%0d",test_case,BITS,borrows,reads);$finish;
    end
    for(integer c=0;c<4;c++)begin
      ack=0;reader_idle=0;start_cut();
      if(test_case!="healthy")negative();
      begin: serial
        integer saved_edges;saved_edges=root_edges;
        for(integer w=0;w<WORDS;w++)begin
          @(negedge clock);#2;address=w;
          #1;check(valid && !word_error && word_data===padded[w*64+:64] && payload===expected,"immutable serial snapshot and padding");
          tick();reads++;
        end
        check(root_edges==saved_edges,"physical clocks held throughout indexed staging reads");
        // An accepted reader remains live while the host asks to release.
        @(negedge clock);#2;borrow_attempt=1;reader_idle=0;
        tick();borrow_attempt=0;
        @(negedge clock);#2;release_request=1;
        #1;check(!valid && !borrow,"release closes new readers before edge");
        tick();release_request=0;
        repeat(7)begin tick();check(hold && mask && phase==4 && !failed,"drain holds physical cut while response is outstanding");end
        check(root_edges==saved_edges,"no release edge before reader drain");
        @(negedge clock);#2;reader_idle=1;
        tick();check(phase==5 && hold && mask && !valid,"drained snapshot releases before physical unmask");
        while(!ready)begin tick();check(!failed,"healthy coordinated physical release");end
        repeat(9+c*13)tick();
        check(root_edges>saved_edges && !hold && !mask,"functional execution resumes after complete drain");
      end
    end
    check(cuts==4 && reads==4*WORDS && borrows==4,"complete serial and outstanding-read scope");
    $display("NATIVE_CAPTURE_PASS bits=%0d cuts=%0d reads=%0d borrows=%0d checks=%0d",BITS,cuts,reads,borrows,checks);$finish;
  end
  initial begin #2000000;check(0,"watchdog");end
endmodule
