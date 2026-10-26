`timescale 1ns/1ps
`ifndef RESTORE_GATES
`define RESTORE_GATES 3
`endif
`ifndef RESTORE_SCHEMA
`define RESTORE_SCHEMA 256'h96c729e8745f16d1
`endif
module transport_control_restore_tb;
  import "DPI-C" function void checkpoint_network_fail();
  localparam GATES=`RESTORE_GATES, BITS=481+GATES, WORDS=(BITS+63)/64;
  localparam [255:0] SCHEMA=`RESTORE_SCHEMA;
  reg clock=0, reset=1;
  always #5 clock=!clock;
  reg begin_restore=0, write_word=0, commit_restore=0, abort_restore=0;
  reg [255:0] header_schema=SCHEMA;
  reg [31:0] header_bits=BITS, header_words=WORDS;
  reg [63:0] header_cycle=0, expected_cycle=0;
  reg [31:0] header_crc32c=0, word_index=0;
  reg [63:0] word_data=0;
  reg cut_valid=1, owners_quiescent=1, owner_error=0, apply_ready=0;
  wire busy, apply_valid, applied;
  wire [BITS-1:0] apply_state;
  wire [63:0] apply_cycle;
  wire [7:0] error;
  CheckpointTransportControlRestore #(.GATES(GATES),.SCHEMA_SHA256(SCHEMA)) dut(.*);
  reg [BITS-1:0] expected=0;
  integer checks=0, restores=0, rejections=0, acks=0, epoch=0, observed_word=0;
  // Independent byte-oriented CRC oracle, rather than the RTL's bit loop.
  function automatic [31:0] checksum(input reg [BITS-1:0] value);
    reg [31:0] crc;
    reg [7:0] octet;
    begin
      crc='1;
      for(integer b=0;b<WORDS*8;b++) begin
        octet=value >> (b*8); crc=crc ^ octet;
        repeat(8) crc=(crc>>1) ^ (crc[0] ? 32'h82f63b78 : 0);
      end
      checksum=~crc;
    end
  endfunction
  task check(input bit ok,input string signal_name);
    checks++;
    if(!ok) begin
      $display("RESTORE_DIVERGENCE cut=%0d signal=%s word=%0d restores=%0d acks=%0d",expected_cycle,signal_name,observed_word,restores,acks);
      $dumpflush; #0.001; checkpoint_network_fail(); $fatal(1,"failure helper returned");
    end
  endtask
  task tick; @(posedge clock); #1; endtask
  task start_edge; @(negedge clock); #1; endtask
  task reset_bank;
    start_edge; reset=1; begin_restore=0; write_word=0; commit_restore=0; abort_restore=0;
    cut_valid=1; owners_quiescent=1; owner_error=0; apply_ready=0;
    header_schema=SCHEMA; header_bits=BITS; header_words=WORDS;
    #0.01; check(!apply_valid && apply_state==0 && apply_cycle==0,"reset invalidation");
    tick; check(error==0 && !busy && !applied,"reset storage");
    start_edge; reset=0;
  endtask
  task begin_epoch;
    start_edge; header_cycle=expected_cycle; header_crc32c=checksum(expected); begin_restore=1;
    tick; check(error==0 && busy && !apply_valid,"begin admission");
    start_edge; begin_restore=0;
  endtask
  task words(input integer count);
    for(integer w=0;w<count;w++) begin
      start_edge; write_word=1; word_index=w; word_data=expected >> (w*64);
      tick; check(error==0 && !apply_valid && apply_state==0 && !applied,"unpublished word");
      // Stall the source bus between every pair of accepted words.
      start_edge; write_word=0; word_index='1; word_data=~word_data;
      tick; check(error==0 && !apply_valid,"load gap");
    end
  endtask
  task offer;
    start_edge; commit_restore=1;
    tick; check(error==0 && !applied,"commit complete image");
    start_edge; commit_restore=0;
    #0.01; check(apply_valid,"offer after command retires");
  endtask
  task compare_words;
    check(apply_cycle===expected_cycle,"saved cycle");
    for(integer w=0;w<WORDS;w++) begin
      observed_word=w;
      check((apply_state >> (w*64) & 64'hffffffffffffffff) ===
            (expected >> (w*64) & 64'hffffffffffffffff),"apply word");
    end
  endtask
  task restore_epoch;
    begin_epoch; words(WORDS); offer;
    // Header and data buses may change after acceptance; applied bits may not.
    header_schema=~SCHEMA; header_cycle=~expected_cycle; header_crc32c=0;
    repeat(3) begin tick; check(apply_valid && !applied,"apply backpressure"); compare_words; end
    start_edge; apply_ready=1;
    #0.01; check(apply_valid,"pre-ack validity"); compare_words;
    tick; acks++; restores++;
    check(applied && !apply_valid && apply_state==0 && apply_cycle==0 && busy,"one-shot apply");
    repeat(3) begin tick; check(!applied && !apply_valid,"no repeated acknowledgement"); end
    start_edge; abort_restore=1; tick; check(!busy && error==0,"explicit epoch retirement");
    start_edge; abort_restore=0; apply_ready=0; header_schema=SCHEMA;
  endtask
  task reject(input [7:0] mask);
    #0.01; check(!apply_valid && apply_state==0 && apply_cycle==0,"pre-edge fault suppresses apply");
    tick;
    check((error & mask)==mask && !applied && !apply_valid,"expected sticky rejection");
    rejections++;
    start_edge; begin_restore=0; write_word=0; commit_restore=0; abort_restore=1;
    cut_valid=1; owners_quiescent=1; owner_error=0; expected_cycle=header_cycle;
    tick; check((error & mask)==mask && !apply_valid && !applied,"abort cannot forgive fault");
  endtask
  initial begin
    $dumpfile("transport-control-restore.vcd"); $dumpvars(0,transport_control_restore_tb);
    reset_bank;
    if(GATES<1 || GATES>65535 || SCHEMA==0) begin
      start_edge; begin_restore=1; header_cycle=expected_cycle; reject(8'h02);
      $display("RESTORE_SPECIALIZATION_REJECT gates=%0d schema_zero=%0d checks=%0d",GATES,SCHEMA==0,checks);
      $finish;
    end
    // Every source bit, including the mixed-edge physical mask and high chunks.
    for(integer i=0;i<BITS;i++) begin
      expected=0; expected[i]=1; expected_cycle=100+i; restore_epoch;
    end
    for(epoch=0;epoch<16;epoch++) begin
      for(integer i=0;i<BITS;i++) expected[i]=$random;
      expected_cycle=64'hffffffff00000000+epoch; restore_epoch;
    end
    expected='1; expected_cycle=777;
    // Invalid header, exact identity, size and source cut binding.
    for(epoch=0;epoch<5;epoch++) begin
      reset_bank; start_edge; header_cycle=expected_cycle; begin_restore=1;
      case(epoch)
        0: header_schema=~SCHEMA;
        1: header_bits=BITS-1;
        2: header_words=WORDS+1;
        3: header_words=WORDS-1;
        4: header_cycle=expected_cycle+1;
      endcase
      reject(epoch==4 ? 8'h80 : 8'h02);
    end
    // Missing/wrong owner on entry, load, offer and ready-to-apply edge.
    for(epoch=0;epoch<12;epoch++) begin
      reset_bank;
      if(epoch>=3) begin_epoch;
      if(epoch>=6) begin words(WORDS); offer; end
      start_edge;
      if(epoch<3) begin begin_restore=1; header_cycle=expected_cycle; end
      if(epoch>=9) apply_ready=1;
      case(epoch%3) 0:cut_valid=0; 1:owners_quiescent=0; 2:owner_error=1; endcase
      reject(8'h04);
    end
    // Drift of expected source label while loading / offered / accepting.
    for(epoch=0;epoch<3;epoch++) begin
      reset_bank; begin_epoch;
      if(epoch>0) begin words(WORDS); offer; end
      start_edge; expected_cycle++; if(epoch==2) apply_ready=1; reject(8'h80);
    end
    // Skipped, huge, overflow-alias, duplicate and out-of-range addresses.
    for(epoch=0;epoch<5;epoch++) begin
      reset_bank; begin_epoch;
      if(epoch==3) words(1);
      start_edge; write_word=1;
      case(epoch) 0:word_index=1; 1:word_index='1; 2:word_index=32'h04000000;
        3:word_index=0; 4:word_index=WORDS; endcase
      word_data=0; reject(8'h08);
    end
    // Truncated image, final padding, damaged payload, wrong CRC.
    reset_bank; begin_epoch; words(WORDS-1); start_edge; commit_restore=1; reject(8'h20);
    if(BITS%64!=0) begin
      reset_bank; begin_epoch; words(WORDS-1); start_edge;
      write_word=1; word_index=WORDS-1; word_data='1; reject(8'h10);
    end
    reset_bank; begin_epoch; words(WORDS-1); start_edge;
    write_word=1; word_index=WORDS-1; word_data=(expected >> (64*(WORDS-1))) ^ 1;
    tick; start_edge; write_word=0; commit_restore=1; reject(8'h40);
    reset_bank; start_edge; header_cycle=expected_cycle; header_crc32c=checksum(expected)^1; begin_restore=1;
    tick; start_edge; begin_restore=0; words(WORDS); start_edge; commit_restore=1; reject(8'h40);
    // Order/conflict faults, including commands on an otherwise valid apply.
    for(epoch=0;epoch<11;epoch++) begin
      reset_bank;
      if(epoch>=2) begin_epoch;
      if(epoch>=4) begin words(WORDS); offer; end
      if(epoch==10) begin start_edge; apply_ready=1; tick; acks++; start_edge; apply_ready=0; end
      start_edge;
      case(epoch)
        0: write_word=1;
        1: commit_restore=1;
        2: begin_restore=1;
        3: begin begin_restore=1; write_word=1; end
        4: begin commit_restore=1; apply_ready=1; end
        5: begin write_word=1; apply_ready=1; end
        6: begin begin_restore=1; apply_ready=1; end
        7: begin abort_restore=1; write_word=1; apply_ready=1; end
        8: begin abort_restore=1; begin_restore=1; end
        9: begin abort_restore=1; commit_restore=1; end
        10: begin_restore=1;
      endcase
      reject(8'h01);
    end
    // Abort/reset invalidate load and offered images before any apply edge.
    for(epoch=0;epoch<4;epoch++) begin
      reset_bank; begin_epoch;
      if(epoch%2) begin words(WORDS); offer; end
      else words(WORDS-1);
      start_edge; apply_ready=1;
      if(epoch<2) abort_restore=1; else reset=1;
      #0.01; check(!apply_valid && apply_state==0,"cancel before ready edge");
      tick; check(!applied && !busy && error==0,"cancel discards complete epoch");
    end
    reset_bank; expected_cycle=999; restore_epoch;
    check(restores==BITS+17 && acks==restores+1,"complete acceptance accounting");
    $display("RESTORE_PASS gates=%0d bits=%0d restores=%0d rejections=%0d checks=%0d acks=%0d",GATES,BITS,restores,rejections,checks,acks);
    $finish;
  end
  initial begin #5000000; check(0,"timeout"); end
endmodule
