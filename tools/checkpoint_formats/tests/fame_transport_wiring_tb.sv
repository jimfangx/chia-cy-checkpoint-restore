`timescale 1ns/1ps
// Existing transport input qualification only. This bench does not install a
// complete physical network or claim capture. Deposits initialize/inject faults
// into the component oracle; no testbench value is a hardware checkpoint donor.
module fame_transport_wiring_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  `include "ports.svh"
  Top dut(.*);
  integer checks=0, acknowledged=0, host_step=0, stalls=0, patterns=0;
  reg [63:0] expected_steps=0, consumed_a=0, consumed_b=0, applied_a=0, applied_b=0;
  reg pending_a=0, pending_b=0, clock_accepted=0, data_accepted=0;
  reg [7:0] state_a=0, state_b=0;
  bit corrupt=0;
  task check(input bit condition,input string name);
    checks++;
    if(!condition)begin
      $display("FAME_TRANSPORT_DIVERGENCE host_step=%0d cycle=%0d acknowledged=%0d signal=%s",host_step,applied_a,acknowledged,name);
      checkpoint_widget_failed();$finish;
    end
  endtask
  task qualify;
    check(`TRANSPORT.target_cycle===applied_a,"actual_transport_applied_label");
    check(`TRANSPORT.owner_present===(ownerPresent & (checkpoint_fame_cut_consistent?3'b111:3'b101)),"actual_present_bits");
    check(`TRANSPORT.owner_frozen===(ownerFrozen & (checkpoint_fame_cut_consistent?3'b111:3'b101)),"mandatory_frozen_bits");
    check(`TRANSPORT.owner_error===(ownerError | (checkpoint_fame_cut_consistent?3'b000:3'b010)),"actual_error_bits");
  endtask
  task compare;
    check(dut.model_.checkpoint_fame_completed_steps===expected_steps,"independent_completed");
    check(dut.model_.checkpoint_fame_clockA_consumed===consumed_a,"independent_consumed_a");
    check(dut.model_.checkpoint_fame_clockB_consumed===consumed_b,"independent_consumed_b");
    check(dut.model_.checkpoint_fame_clockA_applied===applied_a,"independent_applied_a");
    check(dut.model_.checkpoint_fame_clockB_applied===applied_b,"independent_applied_b");
    check(dut.model_.a===state_a && dut.model_.b===state_b,"independent_original_state");
    check(checkpoint_fame_cut_consistent===!hostReset,"independent_consistency");
    check(checkpoint_fame_cut_applied_cycle===applied_a,"applied_output");
    qualify();
  endtask
  task step;
    hostClock=0;#4;
    clock_accepted=model_clocks_sink_valid && model_clocks_sink_ready;
    data_accepted=model_data_sink_valid && model_data_sink_ready;
    if(hostReset)begin
      expected_steps=0;consumed_a=0;consumed_b=0;applied_a=0;applied_b=0;pending_a=0;pending_b=0;
    end else if(clock_accepted)begin
      expected_steps++;
      if(pending_a)begin applied_a++;state_a=state_a+model_data_sink_bits;end
      if(pending_b)begin applied_b++;state_b++;end
      if(model_clocks_sink_bits_A)consumed_a++;
      if(model_clocks_sink_bits_B)consumed_b++;
      pending_a=model_clocks_sink_bits_A;pending_b=model_clocks_sink_bits_B;
    end else stalls++;
    hostClock=1;#4;
  endtask
  initial begin
    $dumpfile("fame-transport.vcd");$dumpvars(0,fame_transport_wiring_tb);
    corrupt=$test$plusargs("corrupt");
    hostClock=0;hostReset=1;transport_reset=1;oldCycle=64'hbad0bad1bad2bad3;
    ownerPresent=7;ownerFrozen=0;ownerError=0;
    dut.model_.a=0;dut.model_.b=0;
    #120;repeat(4)step();hostReset=0;transport_reset=0;
    for(integer i=0;i<512;i++)begin
      host_step=i+1;
      if(!model_clocks_sink_valid || clock_accepted)begin
        model_clocks_sink_valid=(i%11!=3 && i%11!=4);
        model_clocks_sink_bits_A=(i%4!=1);model_clocks_sink_bits_B=(i%3==0);
      end
      if(!model_data_sink_valid || data_accepted)begin
        model_data_sink_valid=(i%7!=2);model_data_sink_bits=i*6+2;
      end
      model_value_source_ready=(i%9!=5 && i%9!=6);model_slow_source_ready=(i%13!=6);
      step();
      if(corrupt && host_step==17)begin
        dut.model_.checkpoint_fame_clockA_applied=applied_a^1;#1;
        check(!checkpoint_fame_cut_consistent && !`TRANSPORT.owner_present[1] &&
          !`TRANSPORT.owner_frozen[1] && `TRANSPORT.owner_error[1],"corruption_revokes_before_edge");
        compare();
      end
      compare();acknowledged++;
    end
    for(integer p=0;p<8;p++)for(integer f=0;f<8;f++)for(integer e=0;e<8;e++)begin
      ownerPresent=p;ownerFrozen=f;ownerError=e;#1;qualify();patterns++;
    end
    // An invalid secondary-domain pending bit must also revoke the selected
    // primary owner; no raw edge or transport response is acknowledged here.
    dut.model_.clockB_enabled=~dut.model_.clockB_enabled;#1;
    check(!checkpoint_fame_cut_consistent,"secondary_domain_invalid");qualify();
    dut.model_.clockB_enabled=pending_b;#1;check(checkpoint_fame_cut_consistent,"secondary_domain_repair");
    ownerPresent=7;ownerFrozen=0;ownerError=0;#1;qualify();
    check(!`TRANSPORT.owner_frozen[1],"witness_cannot_invent_acknowledgement");
    check(expected_steps>100 && applied_a>60 && applied_b>30 && stalls>80 && acknowledged==512,"active_backpressure_scope");
    $display("FAME_TRANSPORT_PASS checks=%0d cycles=512 patterns=%0d stalls=%0d applied=%0d",checks,patterns,stalls,applied_a);$finish;
  end
endmodule
