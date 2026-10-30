`timescale 1ns/1ps
// Component policy equivalence only. Deliberately inject arbitrary raw control
// state, including unreachable combinations, into the actual RTL. This is not
// a capture path, checkpoint donor or CPU acceptance test.
module native_read_policy_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  reg clock=0, reset=0, capture_request=0, release_request=0;
  reg [1:0] owner_present=0, owner_frozen=0, owner_error=0;
  reg reader_idle=0, borrow_attempt=0;
  reg [2:0] injected_phase=0;
  reg [5:0] injected_error=0, injected_snapshot_error=0;
  reg injected_occupied=0, injected_ready=0, injected_failed=0;
  reg [63:0] injected_cycle=0;
  wire failed, valid, borrow_enable;
  integer comparisons=0;
  CheckpointNativeStateCapture #(.BITS(1),.GATES(1),.OWNERS(2),.EXTERNAL_CLOCK_NETWORK(1)) dut(
    .clock(clock),.reset(reset),.capture_request(capture_request),.release_request(release_request),
    .ce(1'b0),.target_cycle(64'b0),.owner_present(owner_present),.owner_frozen(owner_frozen),
    .owner_error(owner_error),.reader_idle(reader_idle),.borrow_attempt(borrow_attempt),
    .live_state(1'b0),.word_address(32'b0),.valid(valid),.borrow_enable(borrow_enable),.failed(failed));
  task compare(input bit ok,input string signal_name,input integer flags);
    comparisons++;
    if(!ok)begin
      $display("NATIVE_READ_POLICY_DIVERGENCE phase=%0d flags=%0d signal=%s comparisons=%0d",
               injected_phase,flags,signal_name,comparisons);
      checkpoint_widget_failed();$finish;
    end
  endtask
  initial begin
    $dumpfile("native-read-policy.vcd");$dumpvars(0,native_read_policy_tb);
    force dut.phase=injected_phase;
    force dut.error=injected_error;
    force dut.snapshot.occupied=injected_occupied;
    force dut.snapshot.error=injected_snapshot_error;
    force dut.snapshot.cut_cycle=injected_cycle;
    force dut.physical_ready=injected_ready;
    force dut.physical_failed=injected_failed;
    for(integer p=0;p<8;p++)begin
      injected_phase=p;
      for(integer flags=0;flags<16384;flags++)begin
        injected_occupied=flags[0];
        injected_snapshot_error=flags[1] ? 6'b100000 : 0;
        injected_error=flags[2] ? 6'b100000 : 0;
        injected_ready=flags[3];injected_failed=flags[4];
        owner_frozen=flags[5] ? 3 : 1;
        owner_present=flags[6] ? 3 : 1;
        owner_error=flags[7] ? 2 : 0;
        reset=flags[8];release_request=flags[9];capture_request=flags[10];
        borrow_attempt=flags[11];reader_idle=flags[12];injected_cycle=flags[13];
        #1;
        compare(failed === (|dut.error || |dut.faults || injected_phase==6),"failed",flags);
        compare(valid === (dut.read_safe && !dut.faults[3]),"valid",flags);
        compare(borrow_enable === (valid && dut.snapshot_borrow),"borrow",flags);
      end
    end
    $display("NATIVE_READ_POLICY_PASS combinations=131072 comparisons=%0d",comparisons);
    $finish;
  end
endmodule
