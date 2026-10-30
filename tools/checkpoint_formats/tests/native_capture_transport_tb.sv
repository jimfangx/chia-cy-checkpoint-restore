`timescale 1ns/1ps
`ifndef CAPTURE_BITS
`define CAPTURE_BITS 1036
`endif
// Independent functional/bank and complete staged-vector stream oracle.
module native_capture_transport_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    localparam integer BITS=`CAPTURE_BITS, WORDS=(BITS+63)/64;
    localparam integer FULL=BITS/64, TAIL=BITS%64;
    localparam integer ENTRIES=1+(FULL!=0)+(TAIL!=0);
    localparam [255:0] HASH=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef;
    reg clock=0, reset=1;
    always #5 clock=!clock;
    wire root_clock, clock_mask, freeze, functional_hold, native_valid, native_failed;
    wire [2:0] gate_clock,captured_ce;
    reg [63:0] target_cycle=0;
    reg [31:0] memory[0:3];
    reg [BITS-1:0] live_state=0;
    wire [BITS-1:0] snapshot_state;
    wire [63:0] native_cut_cycle;
    wire [BITS+629:0] control_state;
    reg [2:0] ce_fault=0;
    wire [2:0] ce=(reset ? 3'b111 : {target_cycle[1],target_cycle[2],!target_cycle[0]}) ^ ce_fault;
    reg [63:0] cycle_fault=0;
    reg [1:0] owner_present=3,owner_frozen=0,owner_error=0;
    reg mmio_valid=0,mmio_write=0,mmio_response_ready=1;
    reg [7:0] mmio_address=0;
    reg [31:0] mmio_wdata=0;
    wire mmio_ready,mmio_response_valid,mmio_response_error;
    wire [31:0] mmio_rdata,descriptor_entry;
    reg alias_descriptor=0;
    wire descriptor_valid=descriptor_entry==0;
    wire [7:0] descriptor_bank=alias_descriptor ? 8'hfc : 8'd1;
    wire [15:0] descriptor_slot=0,descriptor_width=32;
    wire [31:0] descriptor_depth=4;
    wire bank_request_valid,bank_response_ready;
    wire [7:0] bank;
    wire [15:0] slot;
    wire [31:0] address;
    reg bank_response_valid=0,bank_response_error=0;
    reg [63:0] bank_response_data=0;
    reg pending=0,hold_response=0;
    reg [31:0] saved_address=0;
    integer delay_count=0;
    // Exercise an endpoint whose ready already depends on native permission.
    // The wrapper's fault/intent path must not feed that grant back into itself.
    wire bank_request_ready=native_valid && !pending && !bank_response_valid;
    wire reader_idle=!pending && !bank_response_valid;
    wire dma_valid,dma_last,dma_abort;
    wire [511:0] dma_data;
    reg dma_ready=0,hold_dma=0;
    CheckpointNativeCaptureTransport #(.BITS(BITS),.GATES(3),.OWNERS(2),.ENTRIES(1),.MANIFEST_SHA256(HASH)) dut(
        .target_cycle(target_cycle ^ cycle_fault),.*);
    always @(posedge root_clock) begin
        if(reset)target_cycle<=0;
        else target_cycle<=target_cycle+1;
    end
    // Real native storage keeps its raw clock. Its functional writes must stop
    // at the SAME last edge as the masked root, not one transport edge earlier.
    always @(posedge clock) begin
        if(reset)for(integer k=0;k<4;k++)memory[k]<=k+1;
        else if(!functional_hold)for(integer k=0;k<4;k++)
            memory[k]<=(memory[k]*33) ^ (target_cycle[31:0]+k);
    end
    // Models a native raw-clock readout pipeline that continues changing while
    // original functional state is held. Every bit is sampled before borrowing.
    integer native_steps=0,plane=0;
    reg [12:0] captured_planes=0;
    always @(posedge clock) begin
        if(reset)begin live_state<=0;native_steps<=0;end
        else begin
            for(integer k=0;k<BITS;k++)
                live_state[k]<=(((k==0 ? 0 : k==1 ? 8191 : k-1)>>plane)&1) ^ native_steps[0];
            native_steps<=native_steps+1;
        end
    end
    integer checks=0,raw_steps=0,frames=0,words=0,cuts=0,requests=0,dma_stalls=0;
    integer owner_delay=0,live_changes=0,fd=0,restart_checks=0;
    reg armed=0,serial=0;
    reg [BITS-1:0] expected_snapshot=0,raw_oracle=0;
    reg [WORDS*64-1:0] padded;
    reg [31:0] expected_memory[0:3],saved_memory[0:3];
    reg [63:0] expected_cycle=0,saved_cycle=0;
    reg [511:0] held_frame;
    reg stalled=0;
    string test_case,frame_path;
    task check(input bit ok,input string signal_name);
        checks++;
        if(!ok)begin
            $display("NATIVE_TRANSPORT_DIVERGENCE case=%s bits=%0d target_cycle=%0d signal=%s frames_ack=%0d words_ack=%0d requests_ack=%0d",test_case,BITS,target_cycle,signal_name,frames,words,requests);
            checkpoint_widget_failed();$finish;
        end
    endtask
    task tick;@(posedge clock);#2;endtask
    always @(posedge clock or negedge clock)begin
        #1;
        if(armed)begin
            check(native_failed === (|dut.native_capture.error || |dut.native_capture.faults || dut.native_capture.phase==6),
                  "factored native failure matches complete hierarchical fault policy");
            check(native_valid === (dut.native_capture.read_safe && !dut.native_capture.faults[3]),
                  "factored native validity matches complete hierarchical fault policy");
            check(dut.native_borrow === (native_valid && dut.native_capture.snapshot_borrow),
                  "factored native borrow matches original snapshot permission");
        end
    end
    task command(input [31:0] value);
        @(negedge clock);#1;mmio_valid=1;mmio_write=1;mmio_address=0;mmio_wdata=value;
        do begin @(posedge clock);end while(!mmio_ready);
        #2;check(mmio_response_valid && !mmio_response_error,"command acknowledgement");
        @(negedge clock);#1;mmio_valid=0;
    endtask
    always @(posedge clock)begin
        if(reset)begin
            expected_cycle=0;raw_steps=0;raw_oracle=0;
            for(integer k=0;k<4;k++)expected_memory[k]=k+1;
            owner_frozen<=0;owner_delay<=0;
        end else begin
            if(!clock_mask)begin
                for(integer k=0;k<4;k++)expected_memory[k]=(expected_memory[k]*33) ^ (expected_cycle[31:0]+k);
                expected_cycle++;
            end
            // Independent preedge raw-pipeline oracle, not a read of DUT banks.
            if(dut.native_capture.phase==2 && !native_failed)begin
                expected_snapshot=raw_oracle;
                saved_cycle=expected_cycle;
                for(integer k=0;k<4;k++)saved_memory[k]=expected_memory[k];
                captured_planes[plane]=1;
                serial=1;
            end
            // Independent identity-plane oracle: alternating runs of zeros and
            // ones, with opposite anchors, then separately counted edge parity.
            raw_oracle=BITS'(2);
            for(integer code=1;code<BITS-1;code++)
                if((code/(1<<plane))%2)raw_oracle[code+1]=1;
            raw_oracle=raw_oracle ^ {BITS{raw_steps[0]}};
            if(freeze)begin
                owner_delay<=owner_delay+1;
                if(owner_delay>6)owner_frozen<=3;
            end else begin owner_delay<=0;owner_frozen<=0;end
            raw_steps++;
            #1;
            if(armed)begin
                check(target_cycle==expected_cycle,"independent root edge count");
                check(live_state===raw_oracle,"independent native pipeline evolution");
                for(integer k=0;k<4;k++)check(memory[k]===expected_memory[k],"independent original functional state");
                if(native_valid)begin
                    check(serial && snapshot_state===expected_snapshot,"all staged native bits before first bank acknowledgement");
                    check(native_cut_cycle==saved_cycle && target_cycle==saved_cycle,"common target cut");
                    if(live_state!==expected_snapshot)live_changes++;
                end
            end
        end
    end
    always @(negedge clock)begin
        #0.5;dma_ready=!hold_dma && raw_steps%5==0;
    end
    always @(posedge clock)begin
        if(reset)begin pending<=0;bank_response_valid<=0;bank_response_data<=0;end
        else begin
            if(bank_response_valid && bank_response_ready)bank_response_valid<=0;
            if(pending)begin
                delay_count<=delay_count+1;
                if(delay_count>=7 && !hold_response)begin
                    bank_response_valid<=1;pending<=0;
                    bank_response_data<=memory[saved_address];
                end
            end
            if(bank_request_valid && bank_request_ready)begin
                check(native_valid && clock_mask && serial,"bank borrowing only after complete staging");
                check(bank==1 && slot==0 && address<4,"original bank selector");
                saved_address<=address;pending<=1;delay_count<=0;requests++;
            end
        end
    end
    // Compare every output frame BEFORE its accepting edge. A compiled word
    // mutation must stop here without acknowledging the divergent frame.
    always @(negedge clock)begin
        #1;
        if(!reset && dma_valid)begin
            check(native_valid && freeze && clock_mask,"stream qualified by complete native cut");
            if(stalled)check(dma_data===held_frame,"frame stable under DMA backpressure");
            padded=0;padded[BITS-1:0]=expected_snapshot;
            check(dma_data[63:0]==64'h3154504b434d5346 && dma_data[79:64]==1,"frame identity");
            check(dma_data[159:96]==saved_cycle,"frame target cycle");
            if(dma_data[95:80]==1)begin
                check(frames==0 && dma_data[255:224]==ENTRIES && dma_data[511:256]==HASH,"header manifest and complete descriptor count");
            end else if(dma_data[95:80]==2)begin
                check(dma_data[223:160]==words,"data word sequence");
                if(words<4)begin
                    check(dma_data[255:224]==0 && dma_data[287:256]==words && dma_data[303:288]==32 && dma_data[311:304]==1 && dma_data[327:312]==0,"original descriptor shape");
                    check(dma_data[399:336]===64'(saved_memory[words]),"original functional bank data");
                end else begin
                    check(dma_data[399:336]===padded[(words-4)*64+:64],"native snapshot DMA word");
                    check(dma_data[311:304]==8'hfc,"reserved staging bank");
                    if(words-4<FULL)check(dma_data[255:224]==1 && dma_data[327:312]==0 && dma_data[287:256]==words-4 && dma_data[303:288]==64,"full native descriptor shape");
                    else check(dma_data[255:224]==1+(FULL!=0) && dma_data[327:312]==1 && dma_data[287:256]==0 && dma_data[303:288]==TAIL,"tail native descriptor shape");
                end
            end else check(dma_last && words==4+WORDS,"complete trailer");
            held_frame=dma_data;stalled=!dma_ready;if(stalled)dma_stalls++;
        end else stalled=0;
    end
    always @(posedge clock)if(!reset && dma_valid && dma_ready)begin
        if(dma_data[95:80]==2)words++;
        if(fd)for(integer k=0;k<64;k++)$fwrite(fd,"%c",dma_data[k*8+:8]);
        frames++;
    end
    task healthy_cut;
        bit response_stall;
        frames=0;words=0;serial=0;
        frame_path=$sformatf("cut-%0d.frames",cuts);fd=$fopen(frame_path,"wb");check(fd!=0,"frame output");
        command(1);
        while(!dut.transport.cut_complete)tick;
        check(words==4+WORDS && frames==6+WORDS,"complete memory and native stream");
        repeat(11)begin tick;check(clock_mask && freeze && target_cycle==saved_cycle,"publication backpressure");end
        $fclose(fd);fd=0;
        $display("NATIVE_TRANSPORT_CUT ordinal=%0d target_cycle=%0d words=%0d",cuts,saved_cycle,words);
        response_stall=cuts%2!=0;
        mmio_response_ready=!response_stall;
        command(2);cuts++;
        // Offer the next start during release: no accepted command may pass
        // until the prior reader drain and falling-edge mask release finish.
        @(negedge clock);#1;mmio_valid=1;mmio_write=1;mmio_wdata=1;
        while(!dut.native_ready)begin
            #1;check(!mmio_ready,"start backpressure during physical release");
            if(!response_stall)begin
                check(dut.transport_mmio_ready,"no MMIO response can mask native release/start guard");
                restart_checks++;
            end
            tick;
        end
        if(response_stall)repeat(5)begin
                tick;
                check(mmio_response_valid && !mmio_response_error && mmio_rdata==0 && !mmio_ready,
                      "MMIO response retained while native release completes");
            end
        @(negedge clock);#1;mmio_valid=0;
        mmio_response_ready=1;
        while(freeze || clock_mask)tick;
        repeat(35)tick;
    endtask
    initial begin
        if(!$value$plusargs("CASE=%s",test_case))test_case="healthy";
        $dumpfile("native-capture-transport.vcd");$dumpvars(0,native_capture_transport_tb);
        repeat(18)tick;
        @(negedge clock);#2;reset=0;armed=1;
        repeat(25)tick;
        if(test_case=="healthy")begin
            for(integer p=0;p<13;p++)begin
                @(negedge clock);#2;plane=p;repeat(3)tick;healthy_cut;
            end
            check(cuts==13 && requests==52 && dma_stalls>20 && live_changes>20 && restart_checks>0 && captured_planes==13'h1fff,
                  "complete position-distinguishing capture and backpressure scope");
            $display("NATIVE_TRANSPORT_PASS bits=%0d cuts=%0d requests=%0d stalls=%0d changes=%0d",BITS,cuts,requests,dma_stalls,live_changes);
        end else if(test_case=="abort-wait" || test_case=="abort-response" || test_case=="abort-native")begin
            if(test_case=="abort-response")hold_response=1;
            if(test_case=="abort-native")hold_dma=1;
            command(1);
            if(test_case=="abort-response")while(!pending)tick;
            else if(test_case=="abort-native")begin
                // Move past the header and original functional descriptors,
                // then abort with an internal native response outstanding.
                hold_dma=0;
                while(!dut.snapshot_response_valid)tick;
            end
            command(4);
            if(test_case=="abort-response")begin
                repeat(13)begin tick;check(freeze && clock_mask && !bank_request_valid,"aborted reader retains physical hold");end
                hold_response=0;
            end
            while(freeze || clock_mask || !reader_idle || !dut.native_ready)tick;
            check(!dma_valid,"aborted stream cannot publish");
            frames=0;words=0;requests=0;serial=0;repeat(17)tick;healthy_cut;
            check(cuts==1 && requests==4,"fresh capture after abort with no stale response");
            $display("NATIVE_TRANSPORT_RECOVERY_PASS case=%s bits=%0d",test_case,BITS);
        end else begin
            if(test_case=="alias")alias_descriptor=1;
            command(1);
            while(!native_valid)tick;
            @(negedge clock);#2;
            if(test_case=="owner")owner_present=1;
            else if(test_case=="owner-error")owner_error=1;
            else if(test_case=="ce")ce_fault=1;
            else if(test_case=="cycle")cycle_fault=1;
            else if(test_case=="freeze")begin force owner_frozen=1;end
            else check(test_case=="alias","known negative case");
            #1;check(!bank_request_valid && !dma_valid,"fault withdraws permission before acknowledgement");
            repeat(12)tick;
            check(dma_abort && freeze,"failed stream invalidated and held");
            if(test_case!="alias")begin
                command(4);repeat(12)begin tick;check(clock_mask && freeze,"sticky native fault cannot reopen physical clock");end
            end
            check(words==0 && requests==0,"negative stops before data or bank acknowledgement");
            $display("NATIVE_TRANSPORT_NEGATIVE_PASS case=%s bits=%0d acknowledged_words=0 acknowledged_requests=0",test_case,BITS);
        end
        $finish;
    end
    initial begin #2000000;check(0,"bounded watchdog");end
endmodule
