`timescale 1ns/1ps
// Generated FAME + native clock/reset collector component. All deposits below
// are directed component initialization/fault injection, never FPGA transport.
module fame_clock_cut_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg hostClock=0, hostReset=1;
  reg model_clocks_sink_valid=0, model_clocks_sink_bits_A=0, model_clocks_sink_bits_B=0;
  reg model_data_sink_valid=0;
  reg [7:0] model_data_sink_bits=0;
  reg model_value_source_ready=0, model_slow_source_ready=0;
  wire model_clocks_sink_ready, model_data_sink_ready;
  wire model_value_source_valid, model_slow_source_valid;
  wire [7:0] model_value_source_bits, model_slow_source_bits;
  reg checkpoint_f2_controller_reset=1, checkpoint_f2_freeze_request=0;
  reg checkpoint_f2_rst_main_n=1, checkpoint_f2_ddr_ready=1;
  reg [3:0] checkpoint_f2_writer_state=0;
  reg [2:0] checkpoint_f2_owner_present=7;
  wire checkpoint_f2_stopped, checkpoint_f2_read_enable, checkpoint_f2_failed;
  wire [1:0] checkpoint_f2_captured_ce;
  wire [1:0] checkpoint_physical_logical_ce;
  wire [3:0] checkpoint_f2_captured_writers;
  wire [63:0] checkpoint_f2_cut_cycle;
  wire [2:0] checkpoint_f2_physical_error;
  wire [1:0] checkpoint_f2_reset_error;
  wire [80:0] checkpoint_f2_control_state;
  wire checkpoint_f2_clock_mask, checkpoint_f2_functional_reset;
  wire checkpoint_fame_cut_consistent;
  wire [63:0] checkpoint_fame_cut_applied_cycle;
  Top dut(.*);
  wire ref_clock_ready, ref_data_ready, ref_value_valid, ref_slow_valid;
  wire [7:0] ref_value, ref_slow;
  // Reference sees exactly the original functional root clock and held reset.
  // It contains no observers, collector, or added state-access implementation.
  ReferenceTop original(.hostClock(dut.checkpoint_physical_root_gate.O),
    .hostReset(checkpoint_f2_functional_reset),
    .model_clocks_sink_valid(model_clocks_sink_valid), .model_clocks_sink_bits_A(model_clocks_sink_bits_A),
    .model_clocks_sink_bits_B(model_clocks_sink_bits_B), .model_clocks_sink_ready(ref_clock_ready),
    .model_data_sink_valid(model_data_sink_valid), .model_data_sink_bits(model_data_sink_bits),
    .model_data_sink_ready(ref_data_ready), .model_value_source_ready(model_value_source_ready),
    .model_slow_source_ready(model_slow_source_ready), .model_value_source_valid(ref_value_valid),
    .model_slow_source_valid(ref_slow_valid), .model_value_source_bits(ref_value), .model_slow_source_bits(ref_slow));
  integer checks=0, ack=0, step_index=0, stalls=0, cuts=0, mutations=0;
  integer actual_edges_a=0, actual_edges_b=0, fault=-1;
  reg [63:0] consumed_a=0, consumed_b=0, applied_a=0, applied_b=0, steps=0;
  reg pending_a=0, pending_b=0;
  reg [7:0] state_a=0, state_b=0;
  reg sample_tick=0;
  bit corrupt=0, clock_accepted=0, data_accepted=0;
  always @(posedge dut.model_.clockA_buffer.O) if (!hostReset) actual_edges_a++;
  always @(posedge dut.model_.clockB_buffer.O) if (!hostReset) actual_edges_b++;
  task check(input bit condition, input string signal_name);
    checks++;
    if (!condition) begin
      $display("FAME_CUT_DIVERGENCE host_step=%0d cycle=%0d acknowledged=%0d signal=%s",step_index,applied_a,ack,signal_name);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  task compare;
    check(dut.model_.checkpoint_fame_completed_steps===steps,"completed_steps");
    check(dut.model_.checkpoint_fame_clockA_consumed===consumed_a,"clockA_consumed");
    check(dut.model_.checkpoint_fame_clockB_consumed===consumed_b,"clockB_consumed");
    check(dut.model_.checkpoint_fame_clockA_applied===applied_a,"clockA_applied");
    check(dut.model_.checkpoint_fame_clockB_applied===applied_b,"clockB_applied");
    check(dut.model_.clockA_enabled===pending_a && dut.model_.clockB_enabled===pending_b,"pending_flags");
    check(dut.model_.checkpoint_fame_overflow===0,"overflow");
    check(checkpoint_fame_cut_consistent===!checkpoint_f2_functional_reset,"local_consistency");
    check(checkpoint_fame_cut_applied_cycle===applied_a,"applied_label");
    check(actual_edges_a==applied_a && actual_edges_b==applied_b,"independent_native_edges");
    check(dut.model_.a===state_a && dut.model_.b===state_b,"independent_original_state");
    check(dut.model_.a===original.model_.a && dut.model_.b===original.model_.b,"uninstrumented_state");
    check({model_clocks_sink_ready,model_data_sink_ready,model_value_source_valid,model_slow_source_valid,
      model_value_source_bits,model_slow_source_bits}===
      {ref_clock_ready,ref_data_ready,ref_value_valid,ref_slow_valid,ref_value,ref_slow},"all_boundary_outputs");
  endtask
  task step;
    hostClock=0; #4;
    clock_accepted=!checkpoint_f2_clock_mask && model_clocks_sink_valid && model_clocks_sink_ready;
    data_accepted=!checkpoint_f2_clock_mask && model_data_sink_valid && model_data_sink_ready;
    if (!checkpoint_f2_clock_mask) begin
      if (checkpoint_f2_functional_reset) begin
        steps=0; consumed_a=0; consumed_b=0; applied_a=0; applied_b=0; pending_a=0; pending_b=0;
      end else if (clock_accepted) begin
        steps++;
        if (pending_a) begin applied_a++; state_a=state_a+model_data_sink_bits; end
        if (pending_b) begin applied_b++; state_b++; end
        if (model_clocks_sink_bits_A) consumed_a++;
        if (model_clocks_sink_bits_B) consumed_b++;
        pending_a=model_clocks_sink_bits_A; pending_b=model_clocks_sink_bits_B;
      end else stalls++;
    end
    hostClock=1; #4; sample_tick=~sample_tick;
  endtask
  function automatic [63:0] observation(input integer r);
    case (r)
      0: observation=dut.model_.checkpoint_fame_clockA_consumed;
      1: observation=dut.model_.checkpoint_fame_clockA_applied;
      2: observation=dut.model_.checkpoint_fame_clockB_consumed;
      3: observation=dut.model_.checkpoint_fame_clockB_applied;
      4: observation=dut.model_.clockA_enabled;
      5: observation=dut.model_.clockB_enabled;
      6: observation=dut.model_.checkpoint_fame_overflow;
      7: observation=dut.model_.checkpoint_fame_completed_steps;
    endcase
  endfunction
  task deposit(input integer r, input reg [63:0] v);
    case(r)
      0: dut.model_.checkpoint_fame_clockA_consumed=v;
      1: dut.model_.checkpoint_fame_clockA_applied=v;
      2: dut.model_.checkpoint_fame_clockB_consumed=v;
      3: dut.model_.checkpoint_fame_clockB_applied=v;
      4: dut.model_.clockA_enabled=v[0];
      5: dut.model_.clockB_enabled=v[0];
      6: dut.model_.checkpoint_fame_overflow=v[0];
      7: dut.model_.checkpoint_fame_completed_steps=v;
    endcase
  endtask
  task capture;
    checkpoint_f2_freeze_request=1;
    repeat(3) begin step(); compare(); end
    check(checkpoint_f2_read_enable && checkpoint_f2_stopped && !checkpoint_f2_failed,"qualified_cut");
    check(checkpoint_f2_cut_cycle===applied_a,"cut_is_applied_edge_count");
    check(checkpoint_f2_captured_writers===4'hf,"original_shell_writers");
    cuts++;
    $display("FAME_CUT_CAPTURE host_step=%0d applied=%0d consumed=%0d steps=%0d",step_index,applied_a,consumed_a,steps);
  endtask
  task bit_faults;
    reg [63:0] saved;
    for(integer r=0;r<7;r++) begin
      saved=observation(r);
      for(integer b=0;b<(r<4?64:1);b++) begin
        deposit(r,saved^(64'd1<<b)); #1;
        check(!checkpoint_f2_read_enable && !checkpoint_fame_cut_consistent,"bit_fault_revokes_permission");
        mutations++;
        deposit(r,saved); #1;
        check(checkpoint_f2_read_enable && checkpoint_fame_cut_consistent,"repair_without_raw_edge");
      end
    end
    saved=observation(7);deposit(7,0);#1;
    check(!checkpoint_f2_read_enable,"consumed_cannot_exceed_completed");mutations++;
    deposit(7,saved);#1;
    // Carry must survive: a 64-bit wrapped sum would incorrectly accept this.
    deposit(0,0);deposit(1,64'hffffffffffffffff);deposit(4,1);deposit(7,64'hffffffffffffffff);#1;
    check(!checkpoint_f2_read_enable,"reject_65bit_carry");mutations++;
    deposit(0,consumed_a);deposit(1,applied_a);deposit(4,pending_a);deposit(7,steps);#1;
    check(checkpoint_f2_read_enable,"repair_complete_local_owner");
  endtask
  initial begin
    $dumpfile("fame-cut.vcd"); $dumpvars(0,fame_clock_cut_tb);
    corrupt=$test$plusargs("corrupt");
    if ($value$plusargs("fault=%d",fault)) check(fault>=0 && fault<=9,"known_fault");
    dut.model_.a=0;dut.model_.b=0;original.model_.a=0;original.model_.b=0;
    #120;repeat(4)step();
    hostReset=0;checkpoint_f2_writer_state=4'hf;repeat(3)step();checkpoint_f2_controller_reset=0;
    for(integer i=0;i<512;i++) begin
      step_index=i+1;
      if(!model_clocks_sink_valid || clock_accepted) begin
        model_clocks_sink_valid=(i%11!=3 && i%11!=4);
        model_clocks_sink_bits_A=(i%4!=1);model_clocks_sink_bits_B=(i%3==0);
      end
      if(!model_data_sink_valid || data_accepted) begin
        model_data_sink_valid=(i%7!=2);model_data_sink_bits=i*6+2;
      end
      model_value_source_ready=(i%9!=5 && i%9!=6);model_slow_source_ready=(i%13!=6);
      step();
      if(corrupt && step_index==17) deposit(1,applied_a^1);
      compare();ack++;
      if(fault>=0 && step_index==17) begin
        capture();
        if(fault<8) begin
          if(fault==7) deposit(7,0);
          else deposit(fault,observation(fault)^1);
        end else if(fault==8) checkpoint_f2_owner_present=6;
        else begin deposit(0,0);deposit(1,64'hffffffffffffffff);deposit(4,1);deposit(7,64'hffffffffffffffff);end
        #1;check(!checkpoint_f2_read_enable,"fault_immediately_revokes_permission");
        step();check(checkpoint_f2_failed && checkpoint_f2_stopped,"sticky_fault_at_raw_edge");
        checkpoint_f2_freeze_request=0;repeat(3)step();
        check(checkpoint_f2_stopped && !checkpoint_f2_read_enable && ack==17,"failed_cut_cannot_release_or_ack");
        $display("FAME_CUT_REJECT fault=%0d acknowledged=%0d",fault,ack);$finish;
      end
      if(i==72 || i==178 || i==332 || i==494) begin
        capture();
        if(i==178) bit_faults();
        repeat(7)begin step();compare();end
        checkpoint_f2_freeze_request=0;repeat(3)begin step();compare();end
        check(!checkpoint_f2_stopped && !checkpoint_f2_failed,"healthy_release");
      end
    end
    check(steps>100 && applied_a>60 && applied_b>30 && stalls>80 && cuts==4 && mutations==261,"complete_active_cut_scope");
    $display("FAME_CUT_PASS checks=%0d cycles=512 steps=%0d stalls=%0d cuts=%0d mutations=%0d",checks,steps,stalls,cuts,mutations);$finish;
  end
endmodule
