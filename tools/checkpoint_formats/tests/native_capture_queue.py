"""Compose the sequencer with the unchanged, source-bound emitted queue banks.

The unselected sibling runs throughout. Original selected storage uses the
generated logical hold; native readout/forwarding pipelines keep their raw clock.
This fixture deliberately makes no complete CPU or production owner claim.
"""
from pathlib import Path

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests import verify_shared_queue_access as queue

ROOT = Path(__file__).resolve().parents[3]


def wrapper(original):
    ports = """  input wire capture_reset,capture_request,release_request,
  input wire [63:0] target_cycle,
  input wire [31:0] capture_address,
  output wire capture_ready,capture_valid,capture_failed,capture_hold,capture_borrow,
  output wire capture_word_error,capture_root_clock,capture_gate_clock,capture_mask,
  output wire [63:0] capture_word,capture_cycle,
  output wire [1035:0] capture_payload,
  output wire [1186:0] capture_control,
  output wire [2:0] capture_phase,
"""
    require(original.count("module SharedQueueSynthesisTop(\n") == 1, "ambiguous original queue wrapper")
    text = original.replace("module SharedQueueSynthesisTop(\n", "module NativeCaptureQueueTop(\n" + ports)
    for q in range(2):
        for suffix, replacement in (("freeze", "capture_hold"), ("req_valid", f"request{q}"),
                                    ("req_ready", f"raw_ready{q}")):
            name = f"checkpoint_shell_region{q}_ckpt_{suffix}"
            needle = f".{name}({name})"
            require(text.count(needle) == 1, "ambiguous real queue hold/request connection")
            text = text.replace(needle, f".{name}({replacement})")
    declarations = """
  wire raw_ready0,raw_ready1;
  wire request0=checkpoint_shell_region0_ckpt_req_valid && capture_borrow;
  wire request1=checkpoint_shell_region1_ckpt_req_valid && capture_borrow;
"""
    require(text.count("  SharedQueueHost host(") == 1, "ambiguous generated queue instance")
    text = text.replace("  SharedQueueHost host(", declarations + "  SharedQueueHost host(")
    body = """
  assign checkpoint_shell_region0_ckpt_req_ready=raw_ready0 && capture_borrow;
  assign checkpoint_shell_region1_ckpt_req_ready=raw_ready1 && capture_borrow;
  CheckpointNativeStateCapture #(.BITS(1036),.GATES(1),.OWNERS(2)) capture_owner(
    .clock(clock),.reset(capture_reset),.capture_request(capture_request),.release_request(release_request),
    .capture_ready(capture_ready),.ce(1'b1),.target_cycle(target_cycle),
    .owner_present(2'b11),.owner_frozen({2{capture_hold}}),.owner_error(2'b00),
    .reader_idle(raw_ready0 && raw_ready1),
    .borrow_attempt((request0 && raw_ready0) || (request1 && raw_ready1)),
    .live_state({checkpoint_shell_region1_ckpt_native_state,checkpoint_shell_region0_ckpt_native_state}),
    .word_address(capture_address),.root_clock(capture_root_clock),.gate_clock(capture_gate_clock),
    .clock_mask(capture_mask),.functional_hold(capture_hold),.valid(capture_valid),
    .borrow_enable(capture_borrow),.failed(capture_failed),.word_data(capture_word),
    .cut_cycle(capture_cycle),.word_error(capture_word_error),.snapshot_state(capture_payload),
    .captured_ce(),.phase(capture_phase),.error(),.control_state(capture_control));
"""
    require(text.count("endmodule") == 1, "ambiguous queue body")
    return text.replace("endmodule", body + "endmodule")


def bench(generated):
    text = (ROOT / "tools/checkpoint_formats/tests/shared_queue_access_tb.sv").read_text()
    text = text.replace("reg [1:0] freeze=0, request_valid=0,response_ready=0;",
                        "wire [1:0] freeze;\n  reg [1:0] request_valid=0,response_ready=0;")
    start = text.index("  task capture;\n")
    end = text.index("  initial begin\n", start)
    text = text[:start] + text[end:]
    end = text.index("    // Explicitly reject requests outside hold")
    text = text[:end] + """
    check(cuts==4 && reads==180 && capture_cuts==4 && capture_words>100,"four complete automatic cut/read/drain/release sequences");
    $display("NATIVE_CAPTURE_QUEUE_PASS cuts=4 reads=%0d words=%0d changes=%0d target_cycle=%0d",reads,capture_words,capture_changes,target_cycle);
    $finish;
  end
  initial begin #2000000;check(0,"automatic capture watchdog");end
endmodule
"""
    declarations = """
  reg capture_reset=1,capture_request=0,release_request=0,serial_active=0;
  reg [31:0] capture_address=0;
  reg [63:0] target_cycle=0;
  wire capture_ready,capture_valid,capture_failed,capture_hold,capture_borrow;
  assign freeze={2{capture_hold}};
  wire capture_word_error,capture_root_clock,capture_gate_clock,capture_mask;
  wire [63:0] capture_word,capture_cycle;
  wire [1035:0] capture_payload;
  wire [1186:0] capture_control;
  wire [2:0] capture_phase;
  reg [1035:0] expected_capture;
  reg [1087:0] expected_padded;
  integer capture_cuts=0,capture_words=0,capture_changes=0;
  always @(posedge capture_root_clock)if(capture_reset)target_cycle<=0;else target_cycle<=target_cycle+1;
  always @(negedge clock)begin
    #3;
    if(serial_active)begin
      check(capture_valid && !capture_failed && capture_payload===expected_capture,"complete immutable staged queue vector");
      check(!capture_word_error && capture_word===expected_padded[capture_address*64+:64],"every serial snapshot word");
      capture_words++;
      if({native_state[1],native_state[0]}!==expected_capture)capture_changes++;
      capture_address=(capture_address+1)%17;
    end
  end
  task capture;
    integer sibling_before,step_before,saved_cycle,capture_file;
    @(negedge clock);#2;check(capture_ready,"automatic capture ready");capture_request=1;
    @(posedge clock);#2;capture_request=0;
    while(capture_phase!=2)begin @(posedge clock);#2;check(!capture_failed,"bounded physical stop and owner acknowledgement");end
    @(posedge clock);
"""
    for q in range(2):
        binding = queue.canonical_json(Path(generated) / f"shell-{q}-banks-binding.json")
        for row in queue.emitted_observation(generated, q, binding)["state"]:
            declarations += (f"    expected_capture[{q*518+row['offset']} +: {row['width']}] = "
                             f"dut.host.q{q}.{row['emitted_register']};\n")
    declarations += """
    #2;check(capture_valid && capture_borrow && capture_payload===expected_capture,"all 28 actual emitted registers before first bank ack");
    check(capture_cycle==target_cycle && capture_mask,"same physical/native target cut");
    $display("NATIVE_CAPTURE_QUEUE_CUT ordinal=%0d target_cycle=%0d fields=28 bits=1036 reader_ack_before=%0d",cuts,capture_cycle,reads);
    capture_file=$fopen($sformatf("automatic-queue-cut%0d.hex",cuts),"w");
    check(capture_file!=0,"original snapshot output file");$fdisplay(capture_file,"%h",capture_control);$fclose(capture_file);
    expected_padded=0;expected_padded[1035:0]=expected_capture;
    step_before=selected_edges;sibling_before=pushes[2];saved_cycle=target_cycle;
    serial_active=1;capture_cuts++;
    allwords();
    check(selected_edges==step_before && target_cycle==saved_cycle,"zero original functional/target edges during native readout");
    check(pushes[2]>sibling_before+50,"sibling remains active on raw clock");
    // Ask to release after a real RAM request is accepted, before response.
    @(negedge clock);#2;bank[0]=QUEUE0_RAM_BANK;slot[0]=QUEUE0_RAM_SLOT;word_address[0]=0;
    request_valid[0]=1;response_ready[0]=0;
    #1;check(request_ready[0],"real final reader request accepted");
    @(posedge clock);#2;request_valid[0]=0;
    @(negedge clock);#2;serial_active=0;release_request=1;
    #1;check(!capture_borrow && !capture_valid,"release revokes new bank and snapshot acknowledgements before edge");
    @(posedge clock);#2;release_request=0;
    repeat(9)begin
      @(posedge clock);#2;
      check(capture_hold && capture_mask && capture_phase==4 && !capture_failed,"physical/local hold retained while native response is stalled");
      check(selected_edges==step_before && target_cycle==saved_cycle,"no premature edge during backpressured drain");
    end
    check(response_valid[0] && !response_error[0] && response_data[0]===64'(memory[0][0]),"real RAM response still drains after release command");
    @(negedge clock);#2;response_ready[0]=1;
    @(posedge clock);#2;response_ready[0]=0;reads++;
    while(!capture_ready)begin @(posedge clock);#2;check(!capture_failed,"coordinated snapshot then physical release");end
    check(!capture_hold && !capture_mask && !capture_valid,"both owners release only after complete reader drain");
    cuts++;active(45+cuts*7,17+cuts*13);
  endtask
"""
    needle = "  wire [517:0] native_state[0:1];"
    require(text.count(needle) == 1, "ambiguous native boundary")
    task_start = declarations.index("  task capture;\n")
    text = text.replace(needle, needle + declarations[:task_start])
    # VCS resolves task variable references at declaration time. Keep the task
    # after the original scoreboard variables and selector localparams.
    needle = "  initial begin\n"
    require(text.count(needle) == 1, "ambiguous workload block")
    text = text.replace(needle, declarations[task_start:] + needle, 1)
    needle = "  SharedQueueSynthesisTop dut(.clock(clock),.reset(reset),"
    text = text.replace(needle, """  NativeCaptureQueueTop dut(.clock(clock),.reset(reset),
    .capture_reset(capture_reset),.capture_request(capture_request),.release_request(release_request),
    .target_cycle(target_cycle),.capture_address(capture_address),.capture_ready(capture_ready),
    .capture_valid(capture_valid),.capture_failed(capture_failed),.capture_hold(capture_hold),
    .capture_borrow(capture_borrow),.capture_word_error(capture_word_error),.capture_word(capture_word),
    .capture_cycle(capture_cycle),.capture_payload(capture_payload),.capture_control(capture_control),
    .capture_root_clock(capture_root_clock),.capture_gate_clock(capture_gate_clock),
    .capture_mask(capture_mask),.capture_phase(capture_phase),""")
    needle = "reset=0;endpoint_reset=0;armed=1;"
    require(text.count(needle) == 1, "ambiguous reset sequence")
    text = text.replace(needle, "reset=0;endpoint_reset=0;capture_reset=0;armed=1;")
    # Keep both raw native owners and the physical target counter in reset
    # through unmodified vendor glbl startup and real gated reset edges.
    needle = "    repeat(3)@(posedge clock);"
    require(text.count(needle) == 1, "ambiguous initial vendor-clock reset")
    return text.replace(needle, "    repeat(16)@(posedge clock);")
