`timescale 1ns/1ps
module checkpoint_transport_tb;
    reg clock = 0;
    always #5 clock = !clock;
    reg reset=1;
    reg [63:0] target_cycle=100;
    reg [3:0] owner_present=15, owner_frozen=0, owner_error=0;
    wire freeze;
    reg mmio_valid=0, mmio_write=0, mmio_response_ready=0;
    reg [7:0] mmio_address=0;
    reg [31:0] mmio_wdata=0;
    wire mmio_ready, mmio_response_valid, mmio_response_error;
    wire [31:0] mmio_rdata;
    wire [31:0] descriptor_entry;
    wire [7:0] descriptor_bank;
    wire [15:0] descriptor_slot, descriptor_width;
    wire [31:0] descriptor_depth;
    reg missing_descriptor=0, wide_descriptor=0, empty_descriptor=0;
    wire descriptor_valid = !missing_descriptor && descriptor_entry < 3;
    assign descriptor_bank = descriptor_entry + 1;
    assign descriptor_slot = descriptor_entry == 0 ? 2 : descriptor_entry == 1 ? 17 : 7;
    assign descriptor_width = wide_descriptor ? 65 : descriptor_entry == 0 ? 9 :
                              descriptor_entry == 1 ? 64 : 1;
    assign descriptor_depth = empty_descriptor ? 0 : descriptor_entry == 0 ? 3 :
                              descriptor_entry == 1 ? 1 : 2;
    wire bank_request_valid, bank_response_ready;
    reg bank_request_ready=0, bank_response_valid=0, bank_response_error=0;
    wire [7:0] bank;
    wire [15:0] slot;
    wire [31:0] address;
    reg [63:0] bank_response_data=0;
    wire dma_valid, dma_last, dma_abort;
    reg dma_ready=0;
    wire [511:0] dma_data;
`ifndef CHECKPOINT_TRANSPORT_MANIFEST_HASH
`define CHECKPOINT_TRANSPORT_MANIFEST_HASH 256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
`endif
    localparam [255:0] HASH = `CHECKPOINT_TRANSPORT_MANIFEST_HASH;
    CheckpointCaptureTransport #(.OWNERS(4), .ENTRIES(3), .MANIFEST_SHA256(HASH)) dut(.restore_hold(1'b0), .restore_load_pos(1'b0), .restore_state(411'b0), .control_state(), .*);
    integer checks=0, step=0, delay_left=0, requests=0, responses=0;
    integer dma_stalls=0, mmio_stalls=0, successful_captures=0;
    reg pending=0, hold_response=0, inject_bank_error=0, inject_high_bits=0;
    reg force_dma_stall=0, lose_owner_freeze=0, cycle_drift=0;
    reg [8:0] ram [0:2];
    reg [63:0] counter=64'h9876543210000000;
    reg [1:0] flags=2'b01;
    reg [8:0] saved_ram [0:2];
    reg [63:0] saved_counter, expected_cycle;
    reg [1:0] saved_flags;
    reg [63:0] pending_data;
    reg pending_error;
    integer frame_count=0, word_count=0, frame_fd=0, first_frames=0;
    string frames_path;
    reg [511:0] stalled_data;
    reg stalled_last, was_stalled=0;
    reg [31:0] stalled_mmio;
    reg stalled_mmio_error, mmio_was_stalled=0;
    integer i;

    task check(input bit condition, input string label);
        checks=checks+1;
        if (!condition) $fatal(1,"TRANSPORT_FAIL %s step=%0d",label,step);
    endtask
    task tick; @(posedge clock); #1; endtask
    task mmio(input bit write_op, input [7:0] addr, input [31:0] data,
              input bit expect_error, output reg [31:0] result);
        @(negedge clock);
        mmio_valid=1; mmio_write=write_op; mmio_address=addr; mmio_wdata=data;
        do begin @(posedge clock); end while (!mmio_ready);
        #1;
        @(negedge clock); mmio_valid=0;
        check(mmio_response_valid,"MMIO response produced");
        check(mmio_response_error === expect_error,"MMIO error code");
        result=mmio_rdata;
        repeat(3) tick;
        @(negedge clock); mmio_response_ready=1;
        tick;
        @(negedge clock); mmio_response_ready=0;
    endtask
    reg [31:0] result;
    task command(input [31:0] value, input bit expect_error);
        mmio(1,0,value,expect_error,result);
    endtask
    task start_capture;
        frame_count=0; word_count=0;
        command(1,0);
        check(freeze,"start freezes");
    endtask
    task abort_capture;
        command(4,0);
        check(!freeze,"abort releases owners");
    endtask
    task wait_failed;
        while (!dma_abort) tick;
        repeat(3) tick;
        mmio(0,8,0,0,result);
        check(result != 0 && freeze && !dma_valid && !bank_request_valid,
              "fault retains freeze and suppresses transfer");
    endtask
    task healthy_capture;
        start_capture;
        while (frame_count < 8) tick;
        repeat(3) tick;
        check(word_count==6 && freeze,"all words emitted, awaiting publication");
        mmio(0,4,0,0,result);
        check(result[3] && result[1] && !result[0],"complete remains frozen");
        mmio(0,16,0,0,result);
        check(result==expected_cycle[31:0],"MMIO cut label");
        mmio(0,24,0,0,result);
        check(result==6,"MMIO transferred word count");
        command(2,0);
        check(!freeze,"host publication releases cut");
        successful_captures=successful_captures+1;
    endtask

    // Real fixture registers/RAM mutate while running. Freeze acknowledges
    // with a delay but blocks their writes on the request's accepting edge.
    always @(posedge clock) begin
        step <= step+1;
        if (reset) begin
            owner_frozen<=0;
            ram[0]<=9'h123; ram[1]<=9'h045; ram[2]<=9'h1aa;
        end else begin
            owner_frozen <= freeze ? (lose_owner_freeze ? 7 : 15) : 0;
            if (freeze && cycle_drift) target_cycle<=target_cycle+1;
            if (!freeze) begin
                target_cycle<=target_cycle+1;
                ram[0]<=ram[0]+1; ram[1]<=ram[1]+3; ram[2]<=ram[2]+7;
                counter<=counter+64'h123456789;
                flags<=flags+1;
            end
            if (mmio_valid && mmio_ready && mmio_write && mmio_address==0 &&
                mmio_wdata==1 && dut.idle_ready && !freeze)
                $fatal(1,"start did not freeze accepting edge");
            if (mmio_valid && mmio_ready && mmio_write && mmio_address==0 &&
                mmio_wdata==1 && dut.idle_ready) begin
                saved_ram[0]<=ram[0]; saved_ram[1]<=ram[1]; saved_ram[2]<=ram[2];
                saved_counter<=counter; saved_flags<=flags;
                expected_cycle<=target_cycle;
            end
            if (freeze && dut.state != 0 && dut.state != 1 && !dma_abort) begin
                check(ram[0]===saved_ram[0] && ram[1]===saved_ram[1] &&
                      ram[2]===saved_ram[2] && counter===saved_counter && flags===saved_flags,
                      "fixture state stable at atomic cut");
            end
        end
    end

    // Independent bank endpoint: latch request values, respond later, hold
    // valid until consumed. A cancelled response can outlive the cut.
    always @(negedge clock) begin
        dma_ready = !force_dma_stall && (step%5==0 || step%5==3);
        bank_request_ready = !pending && !bank_response_valid && step%3!=0;
    end
    always @(posedge clock) begin
        if (!reset) begin
            if (bank_request_valid && bank_request_ready) begin
                check(!pending && !bank_response_valid && freeze,"one frozen outstanding read");
                pending<=1; delay_left<=2+(step%4); requests<=requests+1;
                pending_error<=inject_bank_error;
                case (bank)
                    1: begin
                        check(slot==2 && address<3,"RAM logical selector");
                        pending_data<=inject_high_bits ? 64'h200 : {55'b0,ram[address]};
                    end
                    2: begin check(slot==17 && address==0,"register selector"); pending_data<=counter; end
                    3: begin check(slot==7 && address<2,"flag selector"); pending_data<=flags[address]; end
                    default: $fatal(1,"invalid bank");
                endcase
            end
            if (pending && !hold_response) begin
                if (delay_left==0) begin
                    pending<=0; bank_response_valid<=1;
                    bank_response_data<=pending_data; bank_response_error<=pending_error;
                end else delay_left<=delay_left-1;
            end
            if (bank_response_valid && bank_response_ready) begin
                bank_response_valid<=0; responses<=responses+1;
            end
            if (was_stalled && !dma_abort) begin
                check(dma_valid && dma_data===stalled_data && dma_last===stalled_last,
                      "DMA payload stable during backpressure");
            end
            was_stalled<=dma_valid && !dma_ready && !dma_abort;
            if (dma_valid && !dma_ready) begin
                stalled_data<=dma_data; stalled_last<=dma_last; dma_stalls<=dma_stalls+1;
            end
            if (mmio_was_stalled) begin
                check(mmio_response_valid && mmio_rdata===stalled_mmio &&
                      mmio_response_error===stalled_mmio_error,"MMIO response stable");
            end
            mmio_was_stalled<=mmio_response_valid && !mmio_response_ready;
            if (mmio_response_valid && !mmio_response_ready) begin
                stalled_mmio<=mmio_rdata; stalled_mmio_error<=mmio_response_error;
                mmio_stalls<=mmio_stalls+1;
            end
            if (dma_valid && dma_ready) begin
                check(freeze && !dma_abort,"DMA only at valid frozen cut");
                check(dma_data[63:0]==64'h3154504b434d5346 && dma_data[79:64]==1,
                      "frame magic/version");
                check(dma_data[159:96]==expected_cycle,"frame target-cycle label");
                if (frame_count==0) begin
                    check(dma_data[95:80]==1 && dma_data[223:160]==0 &&
                          dma_data[255:224]==3 && dma_data[511:256]==HASH && !dma_last,
                          "bound manifest header");
                end else if (dma_data[95:80]==2) begin
                    check(dma_data[223:160]==word_count && !dma_last,"word sequence");
                    case (word_count)
                        0,1,2: check(dma_data[255:224]==0 && dma_data[287:256]==word_count &&
                            dma_data[303:288]==9 && dma_data[311:304]==1 && dma_data[327:312]==2 &&
                            dma_data[399:336]==saved_ram[word_count],"RAM state vs independent oracle");
                        3: check(dma_data[255:224]==1 && dma_data[287:256]==0 &&
                            dma_data[303:288]==64 && dma_data[311:304]==2 && dma_data[327:312]==17 &&
                            dma_data[399:336]==saved_counter,"64-bit state vs independent oracle");
                        4,5: check(dma_data[255:224]==2 && dma_data[287:256]==word_count-4 &&
                            dma_data[303:288]==1 && dma_data[311:304]==3 && dma_data[327:312]==7 &&
                            dma_data[399:336]==saved_flags[word_count-4],"flag state vs independent oracle");
                        default: $fatal(1,"extra word");
                    endcase
                    check(dma_data[511:400]==0 && dma_data[335:328]==0,"reserved data bits zero");
                    word_count=word_count+1;
                end else begin
                    check(dma_data[95:80]==3 && dma_last && word_count==6 &&
                          dma_data[223:160]==6 && dma_data[511:256]==0,"complete trailer");
                end
                if (first_frames==0 && frame_fd) $fdisplay(frame_fd,"%0128h",dma_data);
                frame_count=frame_count+1;
                if (dma_last) first_frames=1;
            end
        end
    end

    initial begin
        if ($value$plusargs("frames=%s",frames_path)) begin
            frame_fd=$fopen(frames_path,"w");
            if (!frame_fd) $fatal(1,"cannot open frame evidence");
        end
        repeat(2) tick;
        @(negedge clock); reset=0;
        mmio(0,32,0,0,result); check(result==3,"entry count");
        for (i=0;i<8;i=i+1) begin
            mmio(0,8'h40+i*4,0,0,result);
            check(result==((HASH>>(32*i)) & 32'hffffffff),"manifest MMIO words");
        end
        mmio(0,3,0,1,result); mmio(1,4,1,1,result); command(3,1);
        healthy_capture;
        repeat(19) tick;
        healthy_capture;

        owner_present=7; start_capture; wait_failed; abort_capture; owner_present=15;
        owner_error=1; start_capture; wait_failed; abort_capture; owner_error=0;
        missing_descriptor=1; start_capture; wait_failed; abort_capture; missing_descriptor=0;
        wide_descriptor=1; start_capture; wait_failed; abort_capture; wide_descriptor=0;
        empty_descriptor=1; start_capture; wait_failed; abort_capture; empty_descriptor=0;
        inject_bank_error=1; start_capture; wait_failed; abort_capture; inject_bank_error=0;
        inject_high_bits=1; start_capture; wait_failed; abort_capture; inject_high_bits=0;

        hold_response=1; start_capture;
        while (!pending) tick;
        command(1,1); // busy requests never restart the cursor
        abort_capture;
        mmio(0,4,0,0,result); check(result[5] && !result[0],"aborted read drains before reuse");
        command(1,1);
        @(negedge clock); hold_response=0;
        while (pending || bank_response_valid) tick;
        repeat(2) tick;
        healthy_capture;

        hold_response=1; start_capture;
        while (!pending) tick;
        command(2,1); // premature publication fails frozen
        wait_failed;
        abort_capture;
        @(negedge clock); hold_response=0;
        while (pending || bank_response_valid) tick;
        repeat(2) tick;
        healthy_capture;

        force_dma_stall=1; start_capture;
        while (!dma_valid) tick;
        repeat(4) tick;
        @(negedge clock); owner_error=2;
        #1; check(!dma_valid && dma_abort,"same-edge owner fault invalidates stalled stream");
        wait_failed; abort_capture;
        @(negedge clock); owner_error=0; force_dma_stall=0;

        hold_response=1; start_capture;
        while (!pending) tick;
        @(negedge clock); lose_owner_freeze=1;
        wait_failed; abort_capture;
        @(negedge clock); lose_owner_freeze=0; hold_response=0;
        while (pending || bank_response_valid) tick;
        repeat(2) tick;

        start_capture;
        @(negedge clock); cycle_drift=1;
        wait_failed;
        @(negedge clock); cycle_drift=0;
        abort_capture;
        healthy_capture;
        check(requests==responses && !pending,"no orphaned bank response");
        check(dma_stalls>20 && mmio_stalls>50,"backpressure exercised");
        check(successful_captures==5,"recovery captures completed");
        if (frame_fd) $fclose(frame_fd);
        $display("CHECKPOINT_TRANSPORT_PASS checks=%0d captures=%0d requests=%0d dma_stalls=%0d mmio_stalls=%0d",
                 checks,successful_captures,requests,dma_stalls,mmio_stalls);
        $finish;
    end
    initial begin #1000000; $fatal(1,"TRANSPORT_TIMEOUT state=%0d",dut.state); end
endmodule
