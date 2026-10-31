`timescale 1ns/1ps
`ifndef SNAPSHOT_BITS
`define SNAPSHOT_BITS 130
`endif
module snapshot_state_bank_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    localparam integer BITS=`SNAPSHOT_BITS, WORDS=(BITS+63)/64, PLANES=$clog2(BITS);
    reg clock=0, reset=1, read_enable=0, request_valid=0, response_ready=0;
    always #5 clock=~clock;
    reg [BITS-1:0] snapshot_state=0;
    reg [7:0] bank=254;
    reg [15:0] slot=17;
    reg [31:0] address=0;
    wire request_ready,response_valid,response_error,failed;
    wire [63:0] response_data;
    wire [66:0] control_state;
    CheckpointSnapshotStateBank #(.BITS(BITS),.SLOT(17)) dut(.*);
    reg [WORDS*64-1:0] padded;
    reg [63:0] expected;
    integer checks=0,requests=0,acks=0,stalls=0;
    string scenario;
    task check(input bit ok,input string signal_name);
        checks++;
        if(!ok)begin
            $display("SNAPSHOT_BANK_DIVERGENCE signal=%s requests=%0d acknowledgements=%0d",signal_name,requests,acks);
            checkpoint_widget_failed();$finish;
        end
    endtask
    task tick;@(posedge clock);#1;endtask
    task neg;@(negedge clock);#1;endtask
    task readword(input [31:0] a,input [7:0] b,input [15:0] s,input bit invalid);
        neg();address=a;bank=b;slot=s;request_valid=1;response_ready=0;
        expected=invalid?0:padded[a*64+:64];
        #1;check(request_ready && !response_valid,"empty bank ready");
        tick();request_valid=0;requests++;
        check(response_valid && response_data===expected && response_error===invalid,"latched exact bank word");
        neg();address=32'hffffffff;bank=255;slot=65535;
        repeat(3)begin
            tick();stalls++;
            check(response_valid && response_data===expected && response_error===invalid && !request_ready,"response survives changed selectors and backpressure");
        end
        neg();response_ready=1;tick();acks++;
        check(!response_valid && !failed,"one response consumed");
    endtask
    initial begin
        $dumpfile("snapshot-bank.vcd");$dumpvars(0,snapshot_state_bank_tb);
        if(!$value$plusargs("CASE=%s",scenario))scenario="healthy";
        repeat(2)tick();neg();reset=0;
        for(integer bit_index=0;bit_index<BITS;bit_index++)snapshot_state[bit_index]=bit_index%7<3;
        padded=0;padded[BITS-1:0]=snapshot_state;
        request_valid=1;
        #1;check(!request_ready && !response_valid && response_data==0,"unqualified cut cannot acknowledge");
        tick();neg();read_enable=1;request_valid=0;
        if(scenario=="healthy")begin
            for(integer w=0;w<WORDS;w++)readword(w,254,17,0);
            // Complete bit-identity planes distinguish every input lane and
            // every word, including large geometries with repeated patterns.
            for(integer plane=0;plane<PLANES;plane++)begin
                neg();read_enable=0;request_valid=0;
                for(integer b=0;b<BITS;b++)snapshot_state[b]=(b>>plane)&1;
                padded=0;padded[BITS-1:0]=snapshot_state;
                tick();neg();read_enable=1;
                for(integer w=0;w<WORDS;w++)readword(w,254,17,0);
            end
            readword(WORDS,254,17,1);
            readword(32'h04000000,254,17,1);
            readword(32'hffffffff,254,17,1);
            readword(0,255,17,1);
            readword(0,254,18,1);
            check(requests==WORDS*(PLANES+1)+5 && acks==requests && stalls==requests*3,"complete bounded selector and bit-identity coverage");
            $display("SNAPSHOT_BANK_PASS bits=%0d words=%0d checks=%0d requests=%0d acknowledgements=%0d",BITS,WORDS,checks,requests,acks);$finish;
        end
        // A fault is introduced after a genuine request and BEFORE its first
        // response edge. Even an already-ready downstream must not consume it.
        neg();request_valid=1;response_ready=0;tick();requests++;
        neg();request_valid=0;response_ready=1;
        if(scenario=="reset")reset=1;else read_enable=0;
        #1;check(!response_valid && !request_ready && response_data==0,"lost permission revokes before edge");
        tick();
        if(scenario!="reset")begin
            check(failed && dut.pending,"failed pending owner remains unacknowledged");
            neg();read_enable=1;
            repeat(3)begin tick();check(failed && !response_valid && !request_ready,"repair cannot clear failed pending transfer");end
        end
        neg();reset=1;tick();neg();reset=0;read_enable=1;
        #1;check(!failed && request_ready && !response_valid,"common reset recovery");
        check(acks==0 && requests==1,"fault before first acknowledgement");
        $display("SNAPSHOT_BANK_NEGATIVE_PASS case=%s requests=1 acknowledgements=0 checks=%0d",scenario,checks);$finish;
    end
    initial begin #1000000;check(0,"watchdog");end
endmodule
