`timescale 1ns/1ps
module f2_generated_cut_tb;
    import "DPI-C" function void checkpoint_widget_failed();
    reg clock=0, reference_clock=0, controller_reset=1, freeze_request=0;
    reg rst_main_n=0, ddr_ready=0, raw_reset_xor=0;
    reg [3:0] owner_present=15, writer_xor=0;
    wire clock_mask, read_enable, failed, axi_reset_n, simulator_reset, functional_reset;
    wire [1:0] logical_ce, captured_ce, reset_error;
    wire [2:0] physical_error;
    wire [3:0] writer_state, captured_writers;
    wire [63:0] target_cycle, cut_cycle;
    wire [7:0] a,b;
    wire [80:0] control_state;
    reg [63:0] held_cycle;
`ifdef CHECKPOINT_NATIVE_BANKS
    `include "bank-selectors.svh"
    reg ckpt_req_valid=0, ckpt_resp_ready=0;
    reg [7:0] ckpt_bank=0;
    reg [15:0] ckpt_slot=0;
    reg [31:0] ckpt_address=0;
    wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error;
    wire [63:0] ckpt_resp_data;
    integer bank_reads=0, bank_stalls=0, drain_stalls=0;
`endif
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
    reg checkpoint_f2_shadow_request=0, checkpoint_f2_shadow_release=0;
    reg [31:0] checkpoint_f2_shadow_word_address=0;
    wire checkpoint_f2_shadow_ready, checkpoint_f2_shadow_valid, checkpoint_f2_shadow_failed;
    wire checkpoint_f2_shadow_word_error;
    wire [63:0] checkpoint_f2_shadow_word_data, checkpoint_f2_shadow_cut_cycle;
    wire [5:0] checkpoint_f2_shadow_error;
    wire [217:0] checkpoint_f2_shadow_control_state;
    reg [146:0] staged_expected;
    integer staged_words=0, staged_captures=0;
    task read_shadow;
        for(integer w=0;w<3;w++)begin
            checkpoint_f2_shadow_word_address=w;#1;
            check(checkpoint_f2_shadow_valid && !checkpoint_f2_shadow_word_error &&
                  checkpoint_f2_shadow_word_data===(({45'b0,staged_expected} >> (w*64)) & 64'hffffffffffffffff),
                  "atomic collector/endpoint word");
            check(checkpoint_f2_shadow_cut_cycle===held_cycle,"atomic collector label");
            staged_words++;
        end
        checkpoint_f2_shadow_word_address=32'hffffffff;#1;
        check(checkpoint_f2_shadow_word_error && checkpoint_f2_shadow_word_data===0,"shadow address bound");
    endtask
    task stage_collector;
        check(!ckpt_req_ready && !ckpt_resp_valid && !checkpoint_f2_shadow_valid,
              "functional banks closed before atomic collector capture");
        staged_expected={control_state,dut.execution.ckpt_saved_error,
                         dut.execution.ckpt_saved_data,dut.execution.ckpt_pending};
        checkpoint_f2_shadow_request=1;#1;
        check(checkpoint_f2_shadow_ready,"collector staging request ready");
        raw_step();checkpoint_f2_shadow_request=0;#1;
        check(checkpoint_f2_shadow_valid && !checkpoint_f2_shadow_failed && ckpt_req_ready,
              "atomic stage opens functional banks");
        staged_captures++;read_shadow();
    endtask
`endif
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
`ifdef CHECKPOINT_NATIVE_BANKS
    task raw_step;
        clock=0;#3;clock=1;#3;held();
    endtask
    task bank_start(input integer bank, input integer slot, input integer address);
        ckpt_bank=bank;ckpt_slot=slot;ckpt_address=address;
        ckpt_req_valid=1;ckpt_resp_ready=0;#1;
        check(ckpt_req_ready && !ckpt_resp_valid,"bank request permission");
        raw_step();ckpt_req_valid=0;#1;
        check(!ckpt_req_ready && ckpt_resp_valid,"bank accepted exactly once");
    endtask
    task bank_read(input integer bank,input integer slot,input integer address,
                   input [63:0] expected,input bit error);
        bank_start(bank,slot,address);
        repeat(4)begin
            // The accepted beat must survive arbitrary selector changes.
            ckpt_bank=255;ckpt_slot=65535;ckpt_address=32'hffffffff;
            raw_step();bank_stalls++;
            check(ckpt_resp_valid && ckpt_resp_data===expected && ckpt_resp_error===error,
                  "bank held complete response under backpressure");
        end
        ckpt_resp_ready=1;raw_step();ckpt_resp_ready=0;#1;
        check(!ckpt_resp_valid && ckpt_req_ready,"bank response acknowledged once");bank_reads++;
    endtask
`endif
    task capture;
        held_cycle=target_cycle;held_words={a,b,target_cycle};held_writers=writer_state;
        freeze_request=1;#1;check(!read_enable,"request not cut acknowledgement");
        clock=0;reference_clock=0;#3;check(clock_mask && !read_enable,"common falling cut");
        clock=1;#3;check(read_enable && !failed,"guarded generated cut ready");
        check(captured_ce===logical_ce,"native CE order");
        held();cuts++;
        $display("F2_GENERATED_CUT_CUT target_cycle=%0d writers=%b",target_cycle,captured_writers);
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
        if(fault=="unstaged-read" && target_cycle==17)begin
            ckpt_req_valid=1;#1;
            check(checkpoint_f2_shadow_failed && !ckpt_req_ready && !ckpt_resp_valid,
                  "read before staging fails without acknowledgement");
            repeat(20)begin raw_step();check(clock_mask && !ckpt_resp_valid,"unstaged read retains cut");end
            $display("F2_STAGED_COLLECTOR_REJECT fault=unstaged-read target_cycle=17 acknowledged_edges=0");$finish;
        end
        stage_collector();
        if((fault=="busy-release" || fault=="duplicate-stage" || fault=="cycle-drift") && target_cycle==17)begin
            if(fault=="busy-release")begin bank_start(CYCLES_BANK,CYCLES_SLOT,0);checkpoint_f2_shadow_release=1;end
            else if(fault=="duplicate-stage")checkpoint_f2_shadow_request=1;
            else force dut.execution.checkpoint_f2_shadow_adapter.target_cycle=64'd18;
            #1;check(checkpoint_f2_shadow_failed && !checkpoint_f2_shadow_valid &&
                     !ckpt_req_ready && !ckpt_resp_valid,"staging protocol fault immediately revokes access");
            freeze_request=0;ckpt_req_valid=0;ckpt_resp_ready=1;
            repeat(20)begin raw_step();check(clock_mask && !checkpoint_f2_shadow_valid,"staging failure retains cut");end
            if(fault=="busy-release")check(dut.execution.ckpt_pending,"busy release retains unacknowledged beat");
            $display("F2_STAGED_COLLECTOR_REJECT fault=%s target_cycle=17 acknowledged_edges=0",fault);$finish;
        end
`endif
        if(corrupt && target_cycle==17)begin
            force dut.execution.left.reset=1;#1;paths();
        end
        if(fault!="" && target_cycle==17)begin
`ifdef CHECKPOINT_NATIVE_BANKS
            bank_start(CYCLES_BANK,CYCLES_SLOT,0);
            check(ckpt_resp_data===held_cycle && !ckpt_resp_error,"pending bank beat before cancellation");
`endif
            if(fault=="release-reset" || fault=="release-ddr")begin
                freeze_request=0;clock=0;#3;clock=1;#3;
`ifdef CHECKPOINT_NATIVE_BANKS
                check(clock_mask && read_enable && ckpt_resp_valid,"release boundary retains outstanding response");
`else
                check(clock_mask && !read_enable,"release validation no functional edge");
`endif
            end
            if(fault=="reset" || fault=="release-reset")begin rst_main_n=0;#0.1;end
            else if(fault=="ddr" || fault=="release-ddr")begin ddr_ready=0;#0.1;end
            else if(fault=="writer")begin writer_xor=1;#0.1;end
            else if(fault=="owner")begin owner_present=7;#0.1;end
            else if(fault=="owner-0")begin owner_present=14;#0.1;end
            else if(fault=="owner-1")begin owner_present=13;#0.1;end
            else if(fault=="owner-2")begin owner_present=11;#0.1;end
            else if(fault=="raw-reset")begin raw_reset_xor=1;#0.1;end
            else check(0,"unknown fault");
            check(failed && !read_enable,"immediate read revocation without raw edge");
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
            check(!checkpoint_f2_shadow_valid && checkpoint_f2_shadow_word_error &&
                  checkpoint_f2_shadow_word_data===0,"cancelled snapshot is not publishable");
`endif
`ifdef CHECKPOINT_NATIVE_BANKS
            ckpt_resp_ready=1;ckpt_req_valid=1;
            check(!ckpt_resp_valid && !ckpt_req_ready,"cancellation revokes both bank handshakes without an edge");
`endif
            rst_main_n=1;ddr_ready=1;#0.1;
            check(failed && !read_enable,"source return cannot repair cut");
            freeze_request=0;
            repeat(16)begin clock=0;#3;clock=1;#3;held();check(failed && !read_enable,"sticky cancellation");end
            writer_xor=0;owner_present=15;
            if(fault=="raw-reset")raw_reset_xor=0;
            repeat(4)begin clock=0;#3;clock=1;#3;held();check(failed && !read_enable,"presence return cannot repair cut");end
`ifdef CHECKPOINT_NATIVE_BANKS
            check(!ckpt_resp_valid && !ckpt_req_ready && dut.execution.ckpt_pending,
                  "cancelled bank beat remains unacknowledged");
`endif
            check(|physical_error,"independent physical error");
            $display("F2_GENERATED_CUT_REJECT fault=%s target_cycle=17 acknowledged_edges=0",fault);$finish;
        end
        repeat(16)begin clock=0;#3;clock=1;#3;held();check(read_enable && !failed,"collection backpressure");stalls++;end
`ifdef CHECKPOINT_NATIVE_BANKS
        bank_read(CYCLES_BANK,CYCLES_SLOT,0,held_cycle,0);
        bank_read(LEFT_BANK,LEFT_SLOT,0,a,0);
        bank_read(RIGHT_BANK,RIGHT_SLOT,0,b,0);
        bank_read(255,65535,0,0,1);
        bank_read(CYCLES_BANK,CYCLES_SLOT,1,0,1);
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
        read_shadow();
        check(staged_expected[65:0] !== {dut.execution.ckpt_saved_error,dut.execution.ckpt_saved_data,
              dut.execution.ckpt_pending},"live endpoint changed while immutable stage retained original state");
`endif
        bank_start(CYCLES_BANK,CYCLES_SLOT,0);
        freeze_request=0;#1;
        check(read_enable && !ckpt_req_ready,"withdrawal blocks requests and drains accepted response");
        repeat(4)begin
            raw_step();drain_stalls++;
            check(read_enable && ckpt_resp_valid && ckpt_resp_data===held_cycle && !ckpt_resp_error,
                  "withdrawal cannot release a stalled response");
        end
        ckpt_resp_ready=1;raw_step();ckpt_resp_ready=0;#1;
        check(!ckpt_resp_valid && !ckpt_req_ready,"drain revoked bank handshakes");
`endif
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
        check(read_enable && clock_mask && checkpoint_f2_shadow_valid,"withdrawal retains staged cut after drain");
        read_shadow();checkpoint_f2_shadow_release=1;#1;
        check(!checkpoint_f2_shadow_valid && !ckpt_req_ready,"release immediately closes banks");
        raw_step();checkpoint_f2_shadow_release=0;#1;
        check(!checkpoint_f2_shadow_valid && !checkpoint_f2_shadow_failed,"idle staging release succeeds");
`endif
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
`ifdef CHECKPOINT_NATIVE_BANKS
        check(bank_reads==20 && bank_stalls==80 && drain_stalls==16,"complete bank readout and drain scope");
        $display("F2_NATIVE_COLLECTOR_BANK_PASS reads=20 response_stalls=80 drain_stalls=16");
`endif
`ifdef CHECKPOINT_COLLECTOR_SNAPSHOT
        check(staged_captures==4 && staged_words==36,"complete collector and endpoint staging scope");
        $display("F2_STAGED_COLLECTOR_PASS captures=4 words=36 bits=147 staging_owner_bits=218");
`endif
        ddr_ready=0;step();step();check(functional_reset,"ordinary DDR loss propagates");
        ddr_ready=1;repeat(4)step();
        rst_main_n=0;#0.1;check(!axi_reset_n,"original asynchronous AXI reset");
        step();rst_main_n=1;repeat(5)step();
        check(failed && !read_enable && !clock_mask,"no silent rearm");
        $display("F2_GENERATED_CUT_PASS checks=%0d cycles=320 cuts=4 stalls=64",checks);$finish;
    end
    initial begin #100000;check(0,"watchdog");end
endmodule
