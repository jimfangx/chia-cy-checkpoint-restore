`timescale 1ns/1ps
`ifndef SNAPSHOT_BITS
`define SNAPSHOT_BITS 130
`endif
// Exercise the actual native cut/staging and MMIO/DMA equations. The new
// functional bank carries the ENTIRE stable native-owner control vector,
// rather than only the already-supported staged payload. Fixture, not F2.
module native_control_bank_transport_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    localparam integer BITS=`SNAPSHOT_BITS, OWNER_BITS=BITS+153;
    localparam integer CONTROL_WORDS=(OWNER_BITS+63)/64, PAYLOAD_WORDS=(BITS+63)/64;
    localparam integer ENTRIES=2+(BITS/64!=0)+(BITS%64!=0);
    localparam [255:0] HASH=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef;
    reg clock=0,reset=1;
    always #5 clock=~clock;
    wire root_clock,clock_mask,freeze,functional_hold,native_valid,native_failed;
    wire [2:0] gate_clock,captured_ce;
    reg [63:0] target_cycle=0;
    wire [2:0] ce={target_cycle[1],target_cycle[2],!target_cycle[0]};
    reg owner_fault=0;
    wire [1:0] owner_present=3,owner_frozen={2{functional_hold}},owner_error={2{owner_fault}};
    reg [BITS-1:0] live_state=0;
    wire [BITS-1:0] snapshot_state;
    wire [63:0] native_cut_cycle;
    wire [BITS+629:0] control_state;
    wire [66:0] native_control_bank_state;
    reg mmio_valid=0,mmio_write=1,mmio_response_ready=1;
    reg [7:0] mmio_address=0;
    reg [31:0] mmio_wdata=0;
    wire mmio_ready,mmio_response_valid,mmio_response_error;
    wire [31:0] mmio_rdata,descriptor_entry;
    string scenario;
    wire descriptor_valid=descriptor_entry==0;
    wire [7:0] descriptor_bank=scenario=="alias" ? 251 : 1;
    wire [15:0] descriptor_slot=0,descriptor_width=64;
    wire [31:0] descriptor_depth=1;
    wire bank_request_valid,bank_response_ready;
    reg bank_response_valid=0;
    wire reader_idle=!bank_response_valid;
    wire bank_request_ready=!bank_response_valid,bank_response_error=0;
    wire [7:0] bank;
    wire [15:0] slot;
    wire [31:0] address;
    wire [63:0] bank_response_data=64'h123456789abcdef0;
    wire dma_valid,dma_last,dma_abort;
    wire [511:0] dma_data;
    reg dma_ready=0;
    CheckpointNativeCaptureTransport #(.BITS(BITS),.GATES(3),.OWNERS(2),.ENTRIES(1),
        .CAPTURE_NATIVE_CONTROL(1),.MANIFEST_SHA256(HASH)) dut(.*);
    always @(posedge clock)begin
        if(reset)bank_response_valid<=0;
        else begin
            if(bank_response_ready && bank_response_valid)bank_response_valid<=0;
            if(bank_request_valid && bank_request_ready)bank_response_valid<=1;
        end
    end
    always @(posedge root_clock)if(reset)target_cycle<=0;else target_cycle<=target_cycle+1;
    // A live native reader continues to advance on the raw clock. The complete
    // donor is sampled independently at the staging edge below.
    integer raw_edges=0,checks=0,frames=0,words=0,cuts=0,stalls=0,requests=0,fd;
    integer control_acks=0;
    reg expect_fault=0;
    reg [BITS-1:0] expected_payload=0;
    reg [OWNER_BITS-1:0] expected_owner=0;
    reg [CONTROL_WORDS*64-1:0] padded_owner;
    reg [PAYLOAD_WORDS*64-1:0] padded_payload;
    reg [63:0] expected_cycle;
    reg was_valid=0;
    string path;
    task check(input bit ok,input string signal_name);
        checks++;
        if(!ok)begin
            $display("CONTROL_BANK_DIVERGENCE signal=%s target_cycle=%0d words=%0d requests=%0d",signal_name,target_cycle,words,requests);
            checkpoint_widget_failed();$finish;
        end
    endtask
    task tick;@(posedge clock);#2;endtask
    task command(input [31:0] value);
        @(negedge clock);#1;mmio_valid=1;mmio_wdata=value;
        do begin @(posedge clock);end while(!mmio_ready);
        #2;check(mmio_response_valid && !mmio_response_error,"MMIO command accepted");
        @(negedge clock);#1;mmio_valid=0;
    endtask
    always @(negedge clock)begin #1;dma_ready=raw_edges%5==0 || raw_edges%5==3;end
    always @(posedge clock)begin
        if(reset)begin raw_edges=0;live_state<=0;was_valid=0;end
        else begin
            // Independent identity-dependent pattern, no hierarchy writes.
            raw_edges++;
            for(integer b=0;b<BITS;b++)live_state[b]<=((b+raw_edges)%13)<6;
            if(dut.native_capture.phase==2)begin expected_payload=live_state;expected_cycle=target_cycle;end
            if(native_valid && !was_valid)begin
                // Reconstruct all twelve original owner register vectors. No
                // composite readout port supplies the expected data.
                expected_owner={6'b0,3'd3,3'b0,expected_cycle,ce,1'b0,1'b1,1'b1,
                    6'b0,expected_cycle,1'b1,expected_payload};
                padded_owner=0;padded_owner[OWNER_BITS-1:0]=expected_owner;
                padded_payload=0;padded_payload[BITS-1:0]=expected_payload;
            end
            was_valid=native_valid;
            if(!expect_fault)check(!native_failed && !native_control_bank_state[66],"healthy owner cut");
            if(native_valid)check(control_state[OWNER_BITS-1:0]===expected_owner,"all owner bits stable at one cut");
            if(bank_request_valid && bank_request_ready)requests++;
            if(dut.control_response_valid && dut.response_ready && dut.control_selected)control_acks++;
            if(dma_valid && !dma_ready)stalls++;
            if(dma_valid && dma_ready)begin
                check(!dma_abort && freeze && dma_data[159:96]==expected_cycle,"DMA cut and permission");
                if(frames==0)check(dma_data[95:80]==1 && dma_data[255:224]==ENTRIES && dma_data[511:256]==HASH,"descriptor manifest");
                else if(dma_data[95:80]==2)begin
                    check(dma_data[223:160]==words && !dma_last,"ordered word sequence");
                    if(words==0)check(dma_data[399:336]===bank_response_data,"original external bank retained");
                    else if(words<=CONTROL_WORDS)begin
                        check(dma_data[255:224]==1 && dma_data[287:256]==words-1 && dma_data[303:288]==64 &&
                            dma_data[311:304]==251 && dma_data[327:312]==0,"control bank selectors");
                        check(dma_data[399:336]===padded_owner[(words-1)*64+:64],"entire native control bank word");
                    end else check(dma_data[399:336]===padded_payload[(words-1-CONTROL_WORDS)*64+:64],"original payload transport retained");
                    words++;
                end else check(dma_last && words==1+CONTROL_WORDS+PAYLOAD_WORDS,"complete trailer");
                $fdisplay(fd,"%0128h",dma_data);frames++;
            end
        end
    end
    initial begin
        $dumpfile("control-bank-transport.vcd");$dumpvars(0,native_control_bank_transport_tb);
        if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
        repeat(3)tick();@(negedge clock);#1;reset=0;
        for(integer cut=0;cut<4;cut++)begin
            repeat(19+cut*11)tick();
            path=$sformatf("cut%0d.frames",cut);fd=$fopen(path,"w");check(fd!=0,"open complete frame log");
            frames=0;words=0;requests=0;command(1);
            if(scenario=="lost-control-cut")begin
                while(!native_control_bank_state[65])begin @(negedge clock);#1;end
                expect_fault=1;owner_fault=1;
                #1;check(!dut.control_response_valid && !native_valid && dma_abort,
                    "owner fault revokes pending native control response before accepting edge");
                tick();
                repeat(3)tick();
                check(native_control_bank_state[66] && native_control_bank_state[65] &&
                    native_failed && freeze && control_acks==0 && words==1,
                    "invalid pending control owner cannot invent a drain acknowledgement");
                $fclose(fd);
                @(negedge clock);#1;reset=1;owner_fault=0;repeat(3)tick();
                @(negedge clock);#1;reset=0;tick();
                check(native_control_bank_state==0 && !native_failed && mmio_ready && !freeze,
                    "common reset recovers failed pending bank and capture sequencer");
                $display("CONTROL_BANK_LOST_CUT_PASS control_acknowledgements=0 common_reset_recovered=1");$finish;
            end
            if(scenario=="abort-control")begin
                while(!native_control_bank_state[65])begin @(negedge clock);#1;end
                mmio_valid=1;mmio_wdata=4;
                // Abort revokes publication immediately, while the cut remains
                // physically frozen for its accepting edge. An already valid
                // response drains on that edge, as in the original transport.
                #1;check(mmio_ready && dma_abort && !dma_valid && native_valid &&
                    dut.control_response_valid && clock_mask,
                    "abort drains only an already valid frozen response and cannot publish it");
                tick();@(negedge clock);#1;mmio_valid=0;
                while(freeze)tick();
                check(!native_failed && native_control_bank_state[66:65]==0 &&
                    control_acks==1 && words==1 && requests==1,
                    "safe abort drains exactly one accepted response without publishing control data");
                $fclose(fd);
                $display("CONTROL_BANK_ABORT_PASS control_acknowledgements=1 safe_drain=1 published_control_words=0");$finish;
            end
            if(scenario=="alias")begin
                while(!dma_abort)tick();
                check(frames==1 && words==0 && requests==0 && !dma_valid && !bank_request_valid,
                    "reserved native control bank rejects original descriptor before word request");
                $fclose(fd);
                $display("CONTROL_BANK_ALIAS_PASS words=0 requests=0");$finish;
            end
            while(frames<CONTROL_WORDS+PAYLOAD_WORDS+3)tick();
            check(requests==1 && words==1+CONTROL_WORDS+PAYLOAD_WORDS,"all original owner/control words");
            $fclose(fd);command(2);
            while(!mmio_ready || freeze)tick();
            cuts++;
        end
        check(cuts==4 && stalls>0,"rolling component cuts and DMA backpressure");
        $display("CONTROL_BANK_TRANSPORT_PASS bits=%0d owner_bits=%0d cuts=4 checks=%0d stalls=%0d",BITS,OWNER_BITS,checks,stalls);$finish;
    end
    initial begin #1000000;check(0,"watchdog");end
endmodule
