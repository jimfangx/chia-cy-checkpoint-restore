`timescale 1ns/1ps
module f2_reset_guard_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    reg clock=0, reference_clock=0, controller_reset=1, freeze_request=0;
    reg rst_main_n=0, ddr_ready=0;
    reg [3:0] owner_present=15, writer_xor=0;
    wire root_clock, clock_mask, read_enable, failed, axi_reset_n, simulator_reset, functional_reset;
    wire [2:0] gate_clock, ce, physical_error;
    wire [3:0] writer_state, captured_writers;
    wire [63:0] target_cycle, cut_cycle;
    wire [95:0] functional_words;
    wire [81:0] control_state;
    F2ResetGuardFixture dut (.*);
    wire ref_axi_reset_n, ref_reset;
    wire [3:0] ref_writers;
    F2ShellResetWriters original (
        .firesim_internal_clock(clock), .rst_main_n(rst_main_n), .ddr_ready_in(ddr_ready),
        .rst_firesim_n_sync(ref_axi_reset_n), .writer_state(ref_writers), .simulator_reset(ref_reset));
    reg [63:0] reference_cycle;
    reg [31:0] reference_words[3];
    wire [95:0] reference_word_view={reference_words[2],reference_words[1],reference_words[0]};
    wire [2:0] reference_gate;
    wire [2:0] reference_ce=ref_reset?3'b111:
        {reference_cycle[1]^reference_cycle[0],reference_cycle[2],!reference_cycle[0]};
    always @(posedge reference_clock)
        if(ref_reset)reference_cycle<=0;else reference_cycle<=reference_cycle+1;
    genvar g;
    generate for(g=0;g<3;g=g+1)begin: reference
        BUFGCE gate(.I(reference_clock),.CE(reference_ce[g]),.O(reference_gate[g]));
        always @(posedge reference_gate[g])
            if(ref_reset)reference_words[g]<=g+1;
            else reference_words[g]<=(reference_words[g]*33)^(reference_cycle[31:0]+g);
    end endgenerate
    integer checks=0, cuts=0, stalls=0, edges=0;
    string fault;
    reg [95:0] held_words;
    reg [3:0] held_writers;
    reg [63:0] held_cycle;
    task check(input bit ok,input string why);
        checks++;
        if(!ok)begin
            $display("F2_RESET_GUARD_DIVERGENCE target_cycle=%0d reason=%s",target_cycle,why);
            $dumpflush;checkpoint_widget_failed();$finish;
        end
    endtask
    task compare;
        check(writer_state===ref_writers,"all original shell writer bits unchanged");
        check(axi_reset_n===ref_axi_reset_n && simulator_reset===ref_reset,"original shell AXI and simulator reset paths");
        check(functional_reset===ref_reset,"zero-latency running reset path");
        check(target_cycle===reference_cycle && functional_words===reference_word_view,"independent original target state and cycle");
    endtask
    task step;
        clock=0;reference_clock=0;#3;clock=1;reference_clock=1;#3;compare();
    endtask
    task held;
        check(clock_mask && root_clock===0 && gate_clock===0,"no physical target edge");
        check(target_cycle===held_cycle && functional_words===held_words && cut_cycle===held_cycle,"complete target readback at immutable cut");
        check(captured_writers===held_writers,"four shell writer snapshot bits");
        check(axi_reset_n===ref_axi_reset_n && writer_state===ref_writers,"ungated original shell writer and AXI reset paths");
        check(functional_reset===0,"functional reset held across source loss");
    endtask
    task capture;
        held_cycle=target_cycle;held_words=functional_words;held_writers=writer_state;
        freeze_request=1;#1;check(!read_enable,"request cannot acknowledge cut");
        clock=0;reference_clock=0;#3;check(clock_mask && !read_enable,"common falling cut before sampling");
        clock=1;#3;check(read_enable && !failed,"valid source-owned cut");
        held();cuts++;
        $display("F2_RESET_GUARD_CUT target_cycle=%0d writers=%b",target_cycle,captured_writers);
        if(fault!="" && target_cycle==17)begin
            if(fault=="release-reset" || fault=="release-ddr")begin
                freeze_request=0;clock=0;#3;clock=1;#3;
                check(clock_mask && !read_enable,"release validation has no target edge");
            end
            // Both source pulses complete without ANY raw clock edge. This
            // models a shell reset that also stops/restarts the clock wizard.
            if(fault=="reset" || fault=="release-reset")begin rst_main_n=0;#0.1;end
            else if(fault=="ddr" || fault=="release-ddr")begin ddr_ready=0;#0.1;end
            else if(fault=="writer")begin writer_xor=1;#0.1;end
            else if(fault=="owner")begin owner_present=7;#0.1;end
            else check(0,"unknown fault");
            check(failed && !read_enable,"asynchronous immediate cancellation before next raw edge");
            // A sub-cycle return must NOT repair the failed capture.
            rst_main_n=1;ddr_ready=1;#0.1;
            check(failed && !read_enable,"source return retains invalid cut without raw edge");
            freeze_request=0;
            repeat(16)begin
                clock=0;#3;clock=1;#3;held();
                check(failed && !read_enable,"sticky rejection despite host withdrawal");
            end
            check(|physical_error,"core independently records invalid owner");
            if(fault!="owner" && fault!="writer")check(control_state[81],"source-loss latch retained");
            if(fault=="writer")check(control_state[80],"writer drift retained");
            writer_xor=0;owner_present=15;
            repeat(4)begin clock=0;#3;clock=1;#3;held();check(failed && !read_enable,"restored presence cannot repair failed cut");end
            $display("F2_RESET_GUARD_REJECT fault=%s target_cycle=17 acknowledged_edges=0",fault);
            $finish;
        end
        repeat(16)begin clock=0;#3;clock=1;#3;held();check(read_enable && !failed,"collection backpressure");stalls++;end
        freeze_request=0;#1;check(!read_enable,"request withdrawal revokes reads");
        clock=0;#3;clock=1;#3;check(clock_mask,"registered release validation");
        clock=0;reference_clock=0;#3;check(!clock_mask && !read_enable,"common falling release");
    endtask
    initial begin
        if(!$value$plusargs("fault=%s",fault))fault="";
        $dumpfile("f2-reset-guard.vcd");$dumpvars(0,f2_reset_guard_tb);
        #120;step();step();rst_main_n=1;step();step();
        check(writer_state===4'b0011 && simulator_reset,"original reset synchronizer pipeline");
        ddr_ready=1;step();check(writer_state===4'b0111 && simulator_reset,"original first DDR-ready stage");
        step();check(writer_state===15 && !simulator_reset && target_cycle==0,"original second DDR-ready stage and early target cut");
        controller_reset=0;
        capture();
        for(integer i=1;i<=320;i++)begin
            step();edges++;
            check(target_cycle==i,"logical target edge labels exclude collector clocks");
            if(i==17 || i==128 || i==256)capture();
        end
        check(cuts==4 && stalls==64 && edges==320,"complete required component scope");
        // Ordinary shell behavior must remain original even after external
        // reset/DDR loss; only capture permission is revoked until reinit.
        ddr_ready=0;step();step();check(functional_reset,"DDR loss propagates unchanged in ordinary execution");
        ddr_ready=1;repeat(4)step();
        rst_main_n=0;#0.1;check(!axi_reset_n,"raw shell reset still asynchronously reaches AXI");
        step();rst_main_n=1;repeat(5)step();
        check(failed && !read_enable && !clock_mask,"source fault is not silently rearmed");
        $display("F2_RESET_GUARD_PASS checks=%0d cycles=320 cuts=4 stalls=64",checks);$finish;
    end
endmodule
