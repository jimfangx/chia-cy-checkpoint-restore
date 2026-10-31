`timescale 1ns/1ps
module f2_generated_cut_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    reg clock=0, reference_clock=0, controller_reset=1, freeze_request=0;
    reg rst_main_n=0, ddr_ready=0;
    reg [3:0] owner_present=15, writer_xor=0;
    wire clock_mask, read_enable, failed, axi_reset_n, simulator_reset, functional_reset;
    wire [1:0] logical_ce, captured_ce, reset_error;
    wire [2:0] physical_error;
    wire [3:0] writer_state, captured_writers;
    wire [63:0] target_cycle, cut_cycle;
    wire [7:0] a,b;
    wire [80:0] control_state;
    F2GeneratedCutFixture dut (.*);
    wire ref_axi_reset_n, ref_reset;
    wire [3:0] ref_writers;
    wire [7:0] ra,rb;
    wire [63:0] reference_cycle;
    F2ShellResetWriters original (
        .firesim_internal_clock(clock), .rst_main_n(rst_main_n), .ddr_ready_in(ddr_ready),
        .rst_firesim_n_sync(ref_axi_reset_n), .writer_state(ref_writers), .simulator_reset(ref_reset));
    ResetRoutingReference reference (.clock(reference_clock), .reset(ref_reset),
        .a(ra), .b(rb), .count(reference_cycle));
    wire root_clock=dut.execution.checkpoint_physical_root_gate_O;
    wire [1:0] gate_clock={dut.execution.right.gate_O,dut.execution.left.gate_O};
    integer checks=0, cuts=0, stalls=0, edges=0;
    string fault;
    bit corrupt;
    reg [79:0] held_words;
    reg [3:0] held_writers;
    reg [63:0] held_cycle;
    task check(input bit ok,input string why);
        checks++;
        if(!ok)begin
            $display("F2_GENERATED_CUT_DIVERGENCE target_cycle=%0d signal=%s acknowledged_edges=0",target_cycle,why);
            $dumpflush;checkpoint_widget_failed();$finish;
        end
    endtask
    task paths;
        check(dut.execution.left.reset===functional_reset,"left.reset");
        check(dut.execution.right.reset===functional_reset,"right.reset");
        check(dut.execution.checkpoint_physical_root_gate.CE===!clock_mask,"root.CE");
        check(dut.execution.left.gate.I===clock && dut.execution.right.gate.I===clock,"native.I");
        check(dut.execution.left.gate.CE===(logical_ce[0] && !clock_mask),"left.CE");
        check(dut.execution.right.gate.CE===(logical_ce[1] && !clock_mask),"right.CE");
    endtask
    task compare;
        paths();
        check(writer_state===ref_writers,"original shell writer bits");
        check(axi_reset_n===ref_axi_reset_n && simulator_reset===ref_reset,"original AXI and simulator resets");
        check(functional_reset===ref_reset,"running reset latency");
        check({a,b,target_cycle}==={ra,rb,reference_cycle},"independent original state and cycle");
    endtask
    task step;
        clock=0;reference_clock=0;#3;clock=1;reference_clock=1;#3;compare();
    endtask
    task held;
        paths();
        check(clock_mask && root_clock===0 && gate_clock===0,"functional_clocks_stopped");
        check({a,b,target_cycle}===held_words && cut_cycle===held_cycle,"complete functional readback");
        check(captured_writers===held_writers,"shell snapshot");
        check(writer_state===ref_writers && axi_reset_n===ref_axi_reset_n,"ungated shell writers and AXI reset");
        check(functional_reset===0,"held functional reset");
    endtask
    task capture;
        held_cycle=target_cycle;held_words={a,b,target_cycle};held_writers=writer_state;
        freeze_request=1;#1;check(!read_enable,"request not cut acknowledgement");
        clock=0;reference_clock=0;#3;check(clock_mask && !read_enable,"common falling cut");
        clock=1;#3;check(read_enable && !failed,"guarded generated cut ready");
        check(captured_ce===logical_ce,"native CE order");
        held();cuts++;
        $display("F2_GENERATED_CUT_CUT target_cycle=%0d writers=%b",target_cycle,captured_writers);
        if(corrupt && target_cycle==17)begin
            force dut.execution.left.reset=1;#1;paths();
        end
        if(fault!="" && target_cycle==17)begin
            if(fault=="release-reset" || fault=="release-ddr")begin
                freeze_request=0;clock=0;#3;clock=1;#3;
                check(clock_mask && !read_enable,"release validation no functional edge");
            end
            if(fault=="reset" || fault=="release-reset")begin rst_main_n=0;#0.1;end
            else if(fault=="ddr" || fault=="release-ddr")begin ddr_ready=0;#0.1;end
            else if(fault=="writer")begin writer_xor=1;#0.1;end
            else if(fault=="owner")begin owner_present=7;#0.1;end
            else check(0,"unknown fault");
            check(failed && !read_enable,"immediate read revocation without raw edge");
            rst_main_n=1;ddr_ready=1;#0.1;
            check(failed && !read_enable,"source return cannot repair cut");
            freeze_request=0;
            repeat(16)begin clock=0;#3;clock=1;#3;held();check(failed && !read_enable,"sticky cancellation");end
            writer_xor=0;owner_present=15;
            repeat(4)begin clock=0;#3;clock=1;#3;held();check(failed && !read_enable,"presence return cannot repair cut");end
            check(|physical_error,"independent physical error");
            $display("F2_GENERATED_CUT_REJECT fault=%s target_cycle=17 acknowledged_edges=0",fault);$finish;
        end
        repeat(16)begin clock=0;#3;clock=1;#3;held();check(read_enable && !failed,"collection backpressure");stalls++;end
        freeze_request=0;#1;check(!read_enable,"withdrawal revokes reads");
        clock=0;#3;clock=1;#3;check(clock_mask,"registered release validation");
        clock=0;reference_clock=0;#3;check(!clock_mask && !read_enable,"common falling release");
    endtask
    initial begin
        corrupt=$test$plusargs("corrupt");if(!$value$plusargs("fault=%s",fault))fault="";
        $dumpfile("f2-generated-cut.vcd");$dumpvars(0,f2_generated_cut_tb);
        #120;step();step();rst_main_n=1;step();step();
        check(writer_state===3 && simulator_reset,"original inner reset pipeline");
        ddr_ready=1;step();check(writer_state===7 && simulator_reset,"original DDR stage one");
        step();check(writer_state===15 && !simulator_reset && target_cycle==0,"original DDR stage two");
        controller_reset=0;capture();
        for(integer i=1;i<=320;i++)begin
            step();edges++;check(target_cycle==i,"logical target cycle labels");
            if(i==17 || i==128 || i==256)capture();
        end
        check(cuts==4 && stalls==64 && edges==320,"full scope");
        ddr_ready=0;step();step();check(functional_reset,"ordinary DDR loss propagates");
        ddr_ready=1;repeat(4)step();
        rst_main_n=0;#0.1;check(!axi_reset_n,"original asynchronous AXI reset");
        step();rst_main_n=1;repeat(5)step();
        check(failed && !read_enable && !clock_mask,"no silent rearm");
        $display("F2_GENERATED_CUT_PASS checks=%0d cycles=320 cuts=4 stalls=64",checks);$finish;
    end
    initial begin #100000;check(0,"watchdog");end
endmodule
