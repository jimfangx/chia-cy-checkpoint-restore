`timescale 1ns/1ps
module rocket_native_queues_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    reg clock=0,reset=1;
    always #5 clock=~clock;
    reg [63:0] target_cycle=0,root_reference=0;
    reg [3:0] owner_present=15,owner_error=0;
    reg mmio_valid=0,mmio_write=0,mmio_response_ready=1,dma_ready=0;
    reg [7:0] mmio_address=0;
    reg [31:0] mmio_wdata=0;
    wire mmio_ready,mmio_response_valid,mmio_response_error;
    wire [31:0] mmio_rdata;
    wire dma_valid,dma_last,dma_abort,functional_hold,native_valid,native_failed,root_clock;
    wire [511:0] dma_data;
    wire [63:0] native_cut_cycle;
    wire [6655:0] snapshot_state;
    wire [7287:0] control_state;
    reg [3:0] enq_valid=0,deq_ready=0;
    reg [511:0] enq_bits[0:3];
    wire [3:0] enq_ready,deq_valid;
    wire [511:0] deq_bits[0:3];
    wire [12:0] count_out[0:3];
    // Initialized by real enqueue traffic only. No deposit or forced RAM state.
    reg [511:0] memory[0:3][0:6143];
    integer wp[0:3],rp[0:3],count[0:3],ra[0:3],pushes[0:3],pops[0:3];
    bit fullflag[0:3];
    integer checks=0,frames=0,words=0,cuts=0,stalls=0,raw_steps=0,fd=0;
    integer active=0,traffic_mode=0;
    reg [6655:0] expected_native;
    reg [63:0] expected_cut;
    reg captured=0,collect=0,priming=0,previous_stall=0;
    reg [511:0] held_frame;
    string test_case;
    task check(input bit ok,input string signal_name);
        checks++;
        if(!ok)begin
            $display("ROCKET_NATIVE_QUEUE_DIVERGENCE case=%s cut=%0d signal=%s frames_ack=%0d words_ack=%0d",test_case,target_cycle,signal_name,frames,words);
            checkpoint_widget_failed();$finish;
        end
    endtask
    function automatic [511:0] pattern(input integer q,input integer index);
        for(integer k=0;k<8;k++)pattern[k*64+:64]=(64'h9e3779b97f4a7c15*(index+1)) ^ (64'h0101010101010101*(q+1)) ^ (64'h100000001*k);
    endfunction
    RocketNativeQueueTop dut(
        .clock(clock),.reset(reset),.target_cycle(target_cycle),.owner_present(owner_present),.owner_error(owner_error),
        .mmio_valid(mmio_valid),.mmio_write(mmio_write),.mmio_response_ready(mmio_response_ready),.dma_ready(dma_ready),
        .mmio_address(mmio_address),.mmio_wdata(mmio_wdata),.mmio_ready(mmio_ready),.mmio_response_valid(mmio_response_valid),
        .mmio_response_error(mmio_response_error),.mmio_rdata(mmio_rdata),.dma_valid(dma_valid),.dma_last(dma_last),
        .dma_abort(dma_abort),.dma_data(dma_data),.functional_hold(functional_hold),.native_valid(native_valid),
        .native_failed(native_failed),.root_clock(root_clock),.native_cut_cycle(native_cut_cycle),.snapshot_state(snapshot_state),.control_state(control_state),
        .lane0_io_enq_valid(enq_valid[0]),
        .lane0_io_enq_bits(enq_bits[0]),
        .lane0_io_enq_ready(enq_ready[0]),
        .lane0_io_deq_valid(deq_valid[0]),
        .lane0_io_deq_bits(deq_bits[0]),
        .lane0_io_deq_ready(deq_ready[0]),
        .lane0_io_count(count_out[0]),
        .lane1_io_enq_valid(enq_valid[1]),
        .lane1_io_enq_bits(enq_bits[1]),
        .lane1_io_enq_ready(enq_ready[1]),
        .lane1_io_deq_valid(deq_valid[1]),
        .lane1_io_deq_bits(deq_bits[1]),
        .lane1_io_deq_ready(deq_ready[1]),
        .lane1_io_count(count_out[1]),
        .lane2_io_enq_valid(enq_valid[2]),
        .lane2_io_enq_bits(enq_bits[2]),
        .lane2_io_enq_ready(enq_ready[2]),
        .lane2_io_deq_valid(deq_valid[2]),
        .lane2_io_deq_bits(deq_bits[2]),
        .lane2_io_deq_ready(deq_ready[2]),
        .lane2_io_count(count_out[2]),
        .lane3_io_enq_valid(enq_valid[3]),
        .lane3_io_enq_bits(enq_bits[3]),
        .lane3_io_enq_ready(enq_ready[3]),
        .lane3_io_deq_valid(deq_valid[3]),
        .lane3_io_deq_bits(deq_bits[3]),
        .lane3_io_deq_ready(deq_ready[3]),
        .lane3_io_count(count_out[3]));
    `include "oracle.svh"
    always @(posedge clock)begin
        if(reset)begin
            target_cycle<=0;raw_steps=0;
            for(integer q=0;q<4;q++)begin wp[q]=0;rp[q]=0;count[q]=0;ra[q]=0;fullflag[q]=0;pushes[q]=0;pops[q]=0;end
        end else begin
            raw_steps++;
            if(dut.capture.transport.native_capture.phase==2)begin
                sample_original_native();expected_cut=target_cycle;captured=1;
            end
            if(active)begin
                for(integer q=0;q<4;q++)begin
                    check(enq_ready[q]==(count[q]<6144) && deq_valid[q]==(count[q]!=0) && count_out[q]==count[q],"original public queue control");
                    if(count[q]!=0)check(deq_bits[q]===memory[q][rp[q]],"original functional queue data");
                end
            end
            if(!functional_hold)begin
                target_cycle<=target_cycle+1;
                for(integer q=0;q<4;q++)begin
                    ra[q]=(deq_ready[q] && count[q]>0) ? (rp[q]+1)%6144 : rp[q];
                    if(enq_valid[q] && enq_ready[q])begin memory[q][wp[q]]=enq_bits[q];wp[q]=(wp[q]+1)%6144;pushes[q]++;end
                    if(deq_ready[q] && deq_valid[q])begin rp[q]=(rp[q]+1)%6144;pops[q]++;end
                    case({enq_valid[q]&&enq_ready[q],deq_ready[q]&&deq_valid[q]})
                        2'b10:begin count[q]++;fullflag[q]=1;end
                        2'b01:begin count[q]--;fullflag[q]=0;end
                    endcase
                end
            end
            if((collect || priming) && dma_valid)begin
                check(!dma_abort && native_valid && functional_hold && !native_failed,"valid complete queue capture frame");
                if(previous_stall)check(dma_data===held_frame,"stable DMA frame under backpressure");
                if(!dma_ready)begin stalls++;held_frame=dma_data;previous_stall=1;end
                else begin
                    check(dma_data[63:0]==64'h3154504b434d5346 && dma_data[79:64]==1 && dma_data[159:96]==expected_cut,"frame identity and common target cut");
                    if(frames==0)check(dma_data[95:80]==1 && dma_data[255:224]==21,"all twenty original owners and native vector header");
                    else if(dma_last)check(dma_data[95:80]==3 && dma_data[223:160]==196728,"complete trailer word count");
                    else begin
                        reg [63:0] expected;
                        integer ordinal,address;
                        ordinal=dma_data[255:224];address=dma_data[287:256];
                        check(dma_data[95:80]==2 && dma_data[223:160]==words,"complete ordered data frame");
                        if(ordinal<20)expected_original_word(ordinal,address,expected);
                        else begin
                            check(ordinal==20 && address<104,"native descriptor ordinal and address");
                            expected=expected_native[address*64+:64];
                        end
                        check(dma_data[399:336]===expected,"every original memory/register and native snapshot word before DMA acknowledgement");
                        words++;
                    end
                    if(fd!=0)for(integer byte_index=0;byte_index<64;byte_index++)$fwrite(fd,"%c",dma_data[byte_index*8+:8]);
                    frames++;previous_stall=0;
                end
            end
        end
    end
    always @(negedge clock)begin
        #2;
        if((collect || priming) && dma_valid && dma_data[95:80]==2)begin
            reg [63:0] expected;
            integer ordinal,address;
            ordinal=dma_data[255:224];address=dma_data[287:256];
            if(ordinal<20)expected_original_word(ordinal,address,expected);
            else begin
                check(ordinal==20 && address<104,"preedge native descriptor");
                expected=expected_native[address*64+:64];
            end
            check(dma_data[399:336]===expected,"preedge original queue/native payload");
        end
    end
    always @(negedge clock)begin
        if(!reset)begin
            // Deterministic independent per-lane backpressure and data histories.
            for(integer q=0;q<4;q++)begin
                enq_valid[q]=traffic_mode==1 || (traffic_mode==2 && (target_cycle+q)%5!=0);
                deq_ready[q]=traffic_mode==2 && (target_cycle+2*q)%7!=0;
                enq_bits[q]=pattern(q,pushes[q]);
            end
            dma_ready=(raw_steps%7!=0 && raw_steps%11!=0) &&
                !(priming && dma_valid && dma_data[95:80]==2 && dma_data[255:224]==20);
        end
    end
    always @(posedge root_clock)begin
        if(reset)root_reference<=0;else root_reference<=root_reference+1;
    end
    always @(negedge clock)begin
        #3;if(active)check(target_cycle===root_reference,"original native functional hold matches every physical root edge");
    end
    task tick;@(posedge clock);#2;endtask
    task command(input [31:0] value);
        @(negedge clock);#1;mmio_valid=1;mmio_write=1;mmio_wdata=value;
        do begin @(posedge clock);end while(!mmio_ready);
        #2;check(mmio_response_valid && !mmio_response_error,"MMIO command acknowledged");
        @(negedge clock);#1;mmio_valid=0;
    endtask
    task prime_native_selectors;
        priming=1;frames=0;words=0;captured=0;previous_stall=0;
        command(1);while(!native_valid)begin tick();check(!native_failed,"diagnostic cut reaches native staging");end
        check(captured && snapshot_state===expected_native,"all 56 original native register vectors sampled at one edge");
        check($isunknown(snapshot_state),"initial unreset selector state remains explicit in diagnostic snapshot");
        // Read all original owners through the real transport. Before the
        // first unresolved staged-native word can be acknowledged, discard
        // this diagnostic capture. No selector is deposited, masked or reset.
        while(!(dma_valid && dma_data[95:80]==2 && dma_data[255:224]==20))tick();
        check(!$isunknown(dut.live_state),"real reader requests resolve every native selector");
        check(words==196624 && frames==196625,"all original queue owners read before selector priming completes");
        $display("ROCKET_NATIVE_SELECTOR_PRIME target_cycle=%0d words=%0d unresolved_staged_word_ack=0",expected_cut,words);
        command(4);while(functional_hold)tick();
        priming=0;frames=0;words=0;captured=0;previous_stall=0;
        check(!dma_valid && !dut.capture.pending,"unpublished diagnostic capture drains and releases");
    endtask
    task capture;
        integer saved_steps;
        frames=0;words=0;captured=0;collect=1;previous_stall=0;
        fd=$fopen($sformatf("queue-cut-%0d.bin",cuts),"wb");check(fd!=0,"capture file opened");
        command(1);
        while(!native_valid)begin tick();check(!native_failed,"all four native owners reach same cut");end
        check(captured && !$isunknown(snapshot_state) && snapshot_state===expected_native && native_cut_cycle==expected_cut,"all 56 original native register vectors sampled at one edge");
        saved_steps=target_cycle;
        while(frames<196730)begin
            tick();check(target_cycle==saved_steps,"no target advancement while queue RAM readers are borrowed");
        end
        collect=0;$fclose(fd);fd=0;
        check(words==196728 && frames==196730,"complete four 6144x512 RAMs plus original registers and native state");
        $display("ROCKET_QUEUE_CUT ordinal=%0d target_cycle=%0d words=%0d frames=%0d",cuts,expected_cut,words,frames);
        command(2);
        while(functional_hold)tick();
        cuts++;
    endtask
    initial begin
        if(!$value$plusargs("case=%s",test_case))test_case="healthy";
        $dumpfile($sformatf("rocket-native-queues-%s.vcd",test_case));$dumpvars(0,rocket_native_queues_tb);
        // Preserve vendor startup and initialize through genuine clock/reset edges.
        repeat(24)tick();@(negedge clock);#1;reset=0;active=1;
        if(test_case=="missing")begin
            owner_present=7;@(negedge clock);#1;mmio_valid=1;mmio_write=1;mmio_wdata=1;
            repeat(12)begin tick();check(!mmio_ready && !functional_hold && !native_valid,"missing queue owner rejects start");end
            $display("ROCKET_NATIVE_QUEUES_NEGATIVE_PASS missing");$finish;
        end
        traffic_mode=1;
        repeat(6146)tick();
        for(integer q=0;q<4;q++)check(count[q]==6144 && pushes[q]==6144,"every original RAM word initialized through enqueue");
        traffic_mode=2;repeat(300)tick();
        if(test_case=="owner-error" || test_case=="abort")begin
            command(1);while(!native_valid)tick();
            while(!(dut.capture.pending && dut.capture.queue_slot==16'd2))tick();
            if(test_case=="owner-error")begin
                @(negedge clock);#1;owner_error=8;
                #1;check(native_failed && !native_valid,"fourth-vector owner fault immediately revokes publication");
                tick();check(functional_hold,"fault holds original queues");
            end else begin
                command(4);while(functional_hold)tick();
                check(!dma_valid && !dut.capture.pending,"abort drains accepted routed reader before release");
                command(1);while(!native_valid)begin tick();check(!native_failed,"capture recovers after routed reader abort");end
                check(snapshot_state===expected_native && native_cut_cycle==expected_cut,"recovered cut stages all four original native owners");
                command(4);while(functional_hold)tick();
                check(!dma_valid && !dut.capture.pending,"recovered capture abort drains before reopening queues");
            end
            $display("ROCKET_NATIVE_QUEUES_NEGATIVE_PASS %s",test_case);$finish;
        end
        prime_native_selectors();
        for(integer c=0;c<4;c++)begin
            repeat(37+c*97)tick();capture();
        end
        repeat(300)tick();
        check(cuts==4 && stalls>1000,"all queue cuts and DMA backpressure");
        for(integer q=0;q<4;q++)check(pushes[q]>6144 && pops[q]>300,"active distinct queue traffic after release");
        $display("ROCKET_NATIVE_QUEUES_PASS cuts=4 checks=%0d stalls=%0d",checks,stalls);$finish;
    end
    initial begin #200000000;check(0,"queue capture watchdog");end
endmodule
