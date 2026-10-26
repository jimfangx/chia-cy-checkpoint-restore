`timescale 1ns/1ps
module checkpoint_cut_tb;
    reg clock = 0;
    always #5 clock = !clock;
    reg reset = 1, request_valid = 0, capture_complete = 0;
    reg publish_release = 0, abort_capture = 0;
    reg [63:0] target_cycle = 64'd123;
    reg [3:0] owner_present = 4'hf, owner_frozen = 0, owner_error = 0;
    wire request_ready, freeze, read_enable, complete, failed;
    wire [63:0] cut_cycle;
    wire [4:0] error;
    integer checks = 0;
    CheckpointCaptureCut #(.OWNERS(4)) dut(.control_state(), .*);

    task tick;
        @(posedge clock); #1;
    endtask
    task check(input bit condition, input string label);
        checks = checks + 1;
        if (!condition) $fatal(1, "CUT_FAIL %s", label);
    endtask
    task start_cut;
        @(negedge clock);
        request_valid = 1;
        #1; check(freeze && request_ready && !read_enable, "accepting edge freezes before reads");
        tick;
        check(cut_cycle == target_cycle && freeze && !request_ready, "authoritative cut latched");
        @(negedge clock); request_valid = 0;
    endtask
    task abort_cut;
        @(negedge clock); abort_capture = 1;
        #1; check(!read_enable && !complete, "abort cannot publish or read");
        tick;
        check(!freeze && request_ready, "explicit abort releases incomplete transfer");
        @(negedge clock); abort_capture = 0;
        owner_present = 4'hf; owner_error = 0; owner_frozen = 0;
    endtask
    task acknowledge;
        owner_frozen = 4'hf;
        tick;
        check(read_enable && freeze && !complete, "read admission waits for all owners");
    endtask

    initial begin
        tick; @(negedge clock); reset = 0;
        start_cut;
        owner_frozen = 4'h7;
        repeat (5) begin tick; check(freeze && !read_enable && !failed, "partial freeze stalls"); end
        @(negedge clock); acknowledge;
        // DMA backpressure is represented by withholding capture_complete.
        repeat (20) begin tick; check(freeze && read_enable && cut_cycle == 123, "capture backpressure holds cut"); end
        @(negedge clock); capture_complete = 1;
        tick; check(complete && freeze && !read_enable, "complete still frozen before host publication");
        @(negedge clock); capture_complete = 0;
        repeat (5) begin tick; check(complete && freeze, "host publication can stall"); end
        @(negedge clock); publish_release = 1;
        tick; check(request_ready && !freeze && !complete, "publication releases exactly once");
        @(negedge clock); publish_release = 0; owner_frozen = 0;

        owner_present = 4'h7; start_cut;
        check(failed && error == 1 && freeze && !read_enable, "missing owner rejects partial capture"); abort_cut;
        owner_error = 4'h2; start_cut;
        check(failed && error == 2 && freeze, "initial owner failure rejects"); abort_cut;
        start_cut; acknowledge;
        @(negedge clock); owner_error = 4'h4; capture_complete = 1;
        #1; check(!read_enable && !complete, "owner fault masks completion on same edge");
        tick; check(failed && error == 2 && freeze, "active owner fault fails frozen");
        capture_complete = 0; abort_cut;
        start_cut; acknowledge;
        @(negedge clock); owner_frozen = 4'hb;
        #1; check(!read_enable, "lost freeze blocks reads immediately");
        tick; check(failed && error == 4 && freeze, "lost freeze fails frozen"); abort_cut;
        start_cut;
        target_cycle = 124;
        tick; check(failed && error == 8 && cut_cycle == 123 && freeze, "target drift preserves recorded cut"); abort_cut;
        start_cut; acknowledge;
        @(negedge clock); publish_release = 1;
        #1; check(!read_enable, "early release masks reads");
        tick; check(failed && error == 16 && freeze, "early release cannot unfreeze");
        @(negedge clock); publish_release = 0; owner_frozen = 0;
        repeat (5) begin tick; check(failed && freeze && !request_ready, "failure requires explicit abort"); end
        abort_cut;

        // A fresh healthy capture after all failures must use its new cut.
        target_cycle = 777; start_cut; acknowledge;
        check(error == 0 && cut_cycle == 777, "new request clears prior errors");
        @(negedge clock); capture_complete = 1;
        tick; check(complete && freeze, "healthy recovery completes");
        @(negedge clock); capture_complete = 0; publish_release = 1;
        tick; check(!freeze && request_ready, "healthy recovery publishes");
        $display("CHECKPOINT_CUT_PASS checks=%0d", checks);
        $finish;
    end
    initial begin #10000; $fatal(1, "CUT_TIMEOUT"); end
endmodule
