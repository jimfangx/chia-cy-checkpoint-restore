`timescale 1ns/1ps
`ifndef PHYSICAL_RESTORE_GATES
`define PHYSICAL_RESTORE_GATES 3
`endif
module physical_transport_restore_tb;
  import "DPI-C" function void checkpoint_network_fail();
  localparam GATES=`PHYSICAL_RESTORE_GATES, BITS=481+GATES, WORDS=(BITS+63)/64;
  localparam [255:0] SCHEMA=256'h96c729e8745f16d1;
  reg clock=0, reset=1;
  always #5 clock=!clock;
  reg direct_valid=0, staged=0;
  reg [BITS-1:0] direct_state=0, expected=0;
  reg [63:0] expected_cycle=100, direct_cycle=100;
  reg cut_valid=1, owners_quiescent=1, owner_error=0;
  wire apply_valid, apply_ready, applied, restore_hold, restore_load_pos, restore_load_neg, busy;
  wire [BITS-1:0] apply_state, restore_state, control_state;
  wire [63:0] apply_cycle;
  wire [4:0] error;
  reg [BITS-1:0] readback_fault=0;
  reg begin_restore=0, write_word=0, commit_restore=0, abort_restore=0;
  reg [255:0] header_schema=SCHEMA;
  reg [31:0] header_bits=BITS, header_words=WORDS, header_crc32c=0, word_index=0;
  reg [63:0] header_cycle=100, word_data=0;
  wire stage_valid, stage_applied, stage_busy;
  wire [BITS-1:0] stage_state;
  wire [63:0] stage_cycle;
  wire [7:0] stage_error;
  assign apply_valid=staged ? stage_valid : direct_valid;
  assign apply_state=staged ? stage_state : direct_state;
  assign apply_cycle=staged ? stage_cycle : direct_cycle;
  CheckpointTransportControlRestore #(.GATES(GATES),.SCHEMA_SHA256(SCHEMA)) staging(
    .clock(clock),.reset(reset),.begin_restore(begin_restore),.write_word(write_word),
    .commit_restore(commit_restore),.abort_restore(abort_restore),.header_schema(header_schema),
    .header_bits(header_bits),.header_words(header_words),.header_cycle(header_cycle),
    .expected_cycle(expected_cycle),.header_crc32c(header_crc32c),.word_index(word_index),
    .word_data(word_data),.cut_valid(cut_valid),.owners_quiescent(owners_quiescent),
    .owner_error(owner_error),.apply_ready(apply_ready && staged),.apply_valid(stage_valid),
    .apply_state(stage_state),.apply_cycle(stage_cycle),.applied(stage_applied),
    .error(stage_error),.busy(stage_busy));
  CheckpointTransportPhysicalRestore #(.GATES(GATES)) supervisor(
    .clock(clock),.reset(reset),.apply_valid(apply_valid),.apply_state(apply_state),
    .apply_cycle(apply_cycle),.expected_cycle(expected_cycle),.cut_valid(cut_valid),
    .owners_quiescent(owners_quiescent),.owner_error(owner_error),.observed_state(control_state ^ readback_fault),
    .apply_ready(apply_ready),.applied(applied),.restore_hold(restore_hold),
    .restore_load_pos(restore_load_pos),.restore_load_neg(restore_load_neg),
    .restore_state(restore_state),.error(error),.busy(busy));
  wire [GATES-1:0] ce={GATES{1'b1}}, gate_clock, captured_ce;
  wire root_clock, clock_mask, freeze, physical_stopped, physical_read_enable, physical_failed;
  wire [63:0] physical_cut_cycle;
  wire [2:0] physical_error;
  reg [63:0] target_cycle=37;
  reg [3:0] owner_present=15, owner_frozen=15, transport_owner_error=0;
  reg mmio_valid=1, mmio_write=1, mmio_response_ready=1;
  wire mmio_ready, mmio_response_valid, mmio_response_error;
  reg [7:0] mmio_address=0;
  reg [31:0] mmio_wdata=1;
  wire [31:0] mmio_rdata, descriptor_entry;
  wire bank_request_valid, bank_response_ready;
  reg bank_request_ready=1, bank_response_valid=1, bank_response_error=0;
  reg [63:0] bank_response_data=64'hddccbbaa99887766;
  wire [7:0] bank;
  wire [15:0] slot;
  wire [31:0] address;
  wire dma_valid, dma_last, dma_abort;
  reg dma_ready=1;
  wire [511:0] dma_data;
  CheckpointPhysicalCaptureTransport #(.GATES(GATES),.OWNERS(4),.ENTRIES(3),
    .RESTORE_ENABLE(1),.MANIFEST_SHA256(SCHEMA)) dut(
    .owner_error(transport_owner_error),.descriptor_valid(1'b1),.descriptor_bank(8'hd3),
    .descriptor_slot(16'h7135),.descriptor_width(16'd64),.descriptor_depth(32'd3),.*);
  integer checks=0, restores=0, rejections=0, acks=0, target_edges=0, pos_writes=0, neg_writes=0;
  reg monitor_writes=0;
  reg [BITS-1:0] reset_expected=0;
  task check(input bit ok,input string signal_name);
    checks++;
    if(!ok) begin
      $display("PHYSICAL_RESTORE_DIVERGENCE cut=%0d signal=%s restores=%0d acks=%0d target_edges=%0d",expected_cycle,signal_name,restores,acks,target_edges);
      $dumpflush; #0.001; checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task compare(input bit positive_only);
    for(integer i=0;i<BITS;i++) if(!positive_only || i!=411)
      check(control_state[i]===expected[i],$sformatf("physical readback bit=%0d",i));
  endtask
  task tick; @(posedge clock); #2; endtask
  task drive; @(negedge clock); #1; endtask
  task reset_epoch;
    drive; reset=1; direct_valid=0; staged=0; monitor_writes=0;
    begin_restore=0; write_word=0; commit_restore=0; abort_restore=0;
    cut_valid=1; owners_quiescent=1; owner_error=0; direct_cycle=expected_cycle; readback_fault=0;
    repeat(3) tick;
    drive; reset=0;
    repeat(3) tick;
    check(error==0 && !applied && !apply_ready,"fresh parked destination");
    check(target_edges==0,"zero initial target edges");
    reset_expected=0; reset_expected[235:204]=32'hffffffff;
    check(control_state===reset_expected,"complete reset readback after partial load");
  endtask
  task wait_done;
    integer deadline;
    deadline=0;
    while(!applied && error==0 && deadline<15) begin tick; deadline++; end
    check(applied && error==0,"verified physical apply");
    compare(0); acks++; restores++;
    drive; direct_valid=0; monitor_writes=0;
    // Host commands, response acceptance and streams remain isolated under hold.
    repeat(4) begin
      mmio_wdata=mmio_wdata^5; bank_response_data=~bank_response_data;
      mmio_response_ready=~mmio_response_ready; dma_ready=~dma_ready;
      tick; compare(0); check(!applied,"one acknowledgement per reset");
    end
    check(restore_hold && target_edges==0,"permanent park after readback");
  endtask
  function automatic [31:0] checksum(input reg [BITS-1:0] value);
    reg [31:0] crc; reg [7:0] octet;
    begin crc='1;
      for(integer b=0;b<WORDS*8;b++) begin
        octet=value >> (b*8); crc=crc ^ octet;
        repeat(8) crc=(crc>>1) ^ (crc[0] ? 32'h82f63b78 : 0);
      end
      checksum=~crc;
    end
  endfunction
  always @(posedge root_clock) target_edges++;
  genvar g;
  generate for(g=0;g<GATES;g++) begin : edge_audit
    always @(posedge gate_clock[g]) target_edges++;
  end endgenerate
  always @(posedge clock) if(!reset && monitor_writes && restore_load_pos) begin
    pos_writes++; #1; compare(1); check(!applied,"no ack before mask/readback");
  end
  always @(negedge clock) if(!reset && monitor_writes && restore_load_neg) begin
    neg_writes++; #0.1; compare(0); check(!applied,"no ack before settled readback");
  end
  always @(posedge clock or negedge clock) begin
    #0.2;
    if(!reset) check(restore_hold && !mmio_ready && !bank_request_valid &&
      !bank_response_ready && !dma_valid && !mmio_response_valid &&
      !physical_read_enable && dma_abort && clock_mask && target_edges==0,"hold isolates owners and clocks");
  end
  initial begin
    $dumpfile("physical-transport-restore.vcd"); $dumpvars(0,physical_transport_restore_tb);
    // Every physical storage bit, including pending response and falling mask.
    for(integer i=0;i<BITS;i++) begin
      expected=0; expected[i]=1; expected_cycle=100+i; reset_epoch;
      drive; direct_state=expected; direct_cycle=expected_cycle; direct_valid=1; monitor_writes=1;
      wait_done;
    end
    for(integer e=0;e<16;e++) begin
      for(integer i=0;i<BITS;i++) expected[i]=$random;
      expected_cycle=64'hffff0000ffffffff+e; reset_epoch;
      drive; direct_state=expected; direct_cycle=expected_cycle; direct_valid=1; monitor_writes=1;
      wait_done;
    end
    // Reject invalid entry certificates before accepting or writing anything.
    for(integer fault=0;fault<4;fault++) begin
      expected='1; expected_cycle=700+fault; reset_epoch;
      drive; direct_valid=1; direct_state=expected;
      case(fault)
        0:cut_valid=0; 1:owners_quiescent=0; 2:owner_error=1;
        3:direct_cycle=expected_cycle+1;
      endcase
      #0.01; check(!restore_load_pos && !restore_load_neg && !apply_ready,"invalid entry suppresses writes");
      repeat(3) tick;
      check(error!=0 && !applied && control_state===reset_expected,"invalid entry leaves all physical state unchanged");
      rejections++;
    end
    // Reset quarantines incomplete positive and negative physical loads.
    for(integer phase=0;phase<4;phase++) begin
      expected='1; expected_cycle=750+phase; reset_epoch;
      drive; direct_valid=1; direct_state=expected;
      repeat(phase+1) tick;
      check(!applied && target_edges==0,"partial apply has no acknowledgement");
      reset_epoch;
      check(error==0 && control_state===reset_expected,"reset discards partial physical load");
    end
    // Current certificates and stable offer are required before every phase.
    for(integer phase=0;phase<4;phase++) for(integer fault=0;fault<8;fault++) begin
      if(fault==6 && phase<2) continue;
      expected='1; expected_cycle=800+phase*8+fault; reset_epoch;
      drive; direct_state=expected; direct_cycle=expected_cycle; direct_valid=1;
      for(integer n=0;n<=phase;n++) tick;
      // Drive midway through low/high half phase, before its next active edge.
      #0.3;
      case(fault)
        0: cut_valid=0;
        1: owners_quiescent=0;
        2: owner_error=1;
        3: direct_cycle=expected_cycle+1;
        4: direct_valid=0;
        5: direct_state=expected^1;
        6: readback_fault=1;
        7: expected_cycle=expected_cycle+1;
      endcase
      #0.01; check(!restore_load_pos && !restore_load_neg && !apply_ready,"same-edge fault inhibits write and ack");
      repeat(3) tick;
      check(error!=0 && !applied && !apply_ready && restore_hold,"sticky phase rejection");
      cut_valid=1; owners_quiescent=1; owner_error=0; direct_valid=1;
      direct_cycle=expected_cycle; direct_state=expected; readback_fault=0;
      repeat(3) begin tick; check(error!=0 && !applied && !apply_ready,"fault cannot be repaired without reset"); end
      rejections++;
    end
    // Real staging words + CRC feed the same physical adapter end to end.
    expected='1; expected_cycle=999; reset_epoch;
    drive; staged=1; header_cycle=expected_cycle; header_crc32c=checksum(expected); begin_restore=1;
    tick; drive; begin_restore=0;
    for(integer w=0;w<WORDS;w++) begin
      drive; write_word=1; word_index=w; word_data=expected >> (w*64);
      tick; drive; write_word=0;
      repeat(2) tick;
      check(!applied && target_edges==0,"staging backpressure adds no target edge");
    end
    drive; commit_restore=1; tick; drive; commit_restore=0; monitor_writes=1;
    wait_done;
    check(stage_applied || !stage_valid,"staged handshake consumed");
    check(restores==BITS+17 && acks==restores && pos_writes==restores && neg_writes==restores,"complete physical write coverage");
    $display("PHYSICAL_RESTORE_PASS gates=%0d bits=%0d restores=%0d rejections=%0d checks=%0d acks=%0d target_edges=%0d",GATES,BITS,restores,rejections,checks,acks,target_edges);
    $finish;
  end
  initial begin #5000000; check(0,"timeout"); end
endmodule
