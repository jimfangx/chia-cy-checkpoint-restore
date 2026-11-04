// Shared-router component only. Endpoints/global clock owners are external.
module region_router_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer N = `REGIONS;
  localparam integer OW = N > 1 ? $clog2(N) : 1;
  localparam integer BITS = OW + 2;
  localparam integer ENABLED = `RESTORE_ENABLED;
  function automatic [N*8-1:0] bases();
    for (integer k=0; k<N; k++) bases[k*8 +: 8] = k;
  endfunction
  function automatic [N*16-1:0] ce_bases();
    for (integer k=0; k<N; k++) ce_bases[k*16 +: 16] = k;
  endfunction
  reg clock=0, reset=1;
  always #5 clock=~clock;
  reg request_valid=0, response_ready=0;
  reg [7:0] bank=0;
  reg [15:0] slot=0;
  reg [31:0] address=32'h12345678;
  wire request_ready, response_valid, response_error;
  wire [63:0] response_data;
  wire [N-1:0] region_request_valid, region_response_ready;
  wire [7:0] region_bank;
  wire [15:0] region_slot;
  wire [31:0] region_address;
  reg [N-1:0] region_request_ready='1, region_response_valid='1, region_response_error='0;
  reg [N*64-1:0] region_response_data;
  reg restore_hold=0, restore_load=0;
  reg [BITS-1:0] restore_state=0;
  wire [BITS-1:0] capture_state;
  wire restore_error;
  integer checks=0, snapshots=0, blocked_edges=0, acks=0, encodings=0;
  integer fd, code, word;
  string mode, path;
  CheckpointRegionStateRouter #(.REGIONS(N), .BANK_BASE(bases()), .BANK_COUNT({N{8'd1}}),
    .CE_BASE(ce_bases()), .CE_COUNT({N{16'd1}}), .RESTORE_SUPPORTED(ENABLED)) dut(.*);
  task check(input bit ok, input string why);
    checks++;
    if (!ok) begin
      $display("ROUTER_RESTORE_FAIL regions=%0d mode=%s checks=%0d %s",N,mode,checks,why);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  task tick;
    @(posedge clock); #1;
  endtask
  task blocked;
    check({request_ready,response_valid,region_request_valid,region_response_ready} === '0,
      "all four handshake directions blocked before edge");
    blocked_edges++;
  endtask
  task save_word(input integer expected);
    check(capture_state === BITS'(expected),"independent donor state encoding");
    $fdisplay(fd,"%x",capture_state); snapshots++;
  endtask
  task donor;
    fd=$fopen(path,"w"); check(fd!=0,"open donor file");
    save_word(0);
    // Accept the last endpoint, then change selectors under backpressure.
    @(negedge clock); request_valid=1; bank=N-1; slot=7;
    #1; check(request_ready && region_request_valid[N-1] && region_bank==0 && region_slot==7 &&
      region_address==address,"functional request routes exactly once");
    tick(); request_valid=0;
    @(negedge clock); bank=254; slot=65535;
    repeat(3) begin tick(); check(response_valid && !request_ready && response_data==64'hcafe0000+N-1,
      "outstanding owner retained across selector change"); end
    save_word((N-1)*4+1);
    @(negedge clock); response_ready=1;
    tick(); response_ready=0; save_word((N-1)*4);
    // CE request exercises the other selector namespace, with the same owner.
    @(negedge clock); request_valid=1; bank=255; slot=N-1;
    #1; check(request_ready && region_request_valid[N-1] && region_bank==255 && region_slot==0,
      "physical CE local slot rebasing");
    tick(); request_valid=0;
    @(negedge clock); response_ready=1;
    tick(); response_ready=0;
    // An unmapped CE has no endpoint but owns a pending error response.
    @(negedge clock); request_valid=1; bank=255; slot=N;
    #1; check(request_ready && region_request_valid=='0,"invalid request accepted without endpoint");
    tick(); request_valid=0;
    check(response_valid && response_error && response_data==0,"pending invalid response");
    save_word(3);
    @(negedge clock); response_ready=1;
    tick(); response_ready=0; save_word(2);
    $fclose(fd);
    check(snapshots==5,"all donor inactive/pending/error states retained");
  endtask
  task destination;
    fd=$fopen(path,"r"); check(fd!=0,"open independent source image");
    while (!$feof(fd)) begin
      code=$fscanf(fd,"%x\n",word);
      if (code==1) begin
        @(negedge clock); restore_hold=1; restore_load=1;
        restore_state=BITS'(word);
        if ($test$plusargs("corrupt")) restore_state=restore_state ^ BITS'(2);
        request_valid=1; response_ready=1; bank=N-1; slot=7;
        #1; blocked(); check(!restore_error,"valid load under hold");
        tick(); restore_load=0;
        // The donor word is the oracle, never the potentially corrupted input.
        if (capture_state !== BITS'(word) && $test$plusargs("corrupt")) begin
          blocked();
          $display("ROUTER_FIRST_DIVERGENCE signal=capture_state snapshot=%0d expected=%0h observed=%0h acknowledged_edges=%0d",snapshots,word,capture_state,acks);
          checkpoint_widget_failed(); $finish;
        end
        check(capture_state === BITS'(word),"complete zero-transaction-edge destination readback");
        repeat(5) begin
          @(negedge clock); region_request_ready=~region_request_ready;
          region_response_valid=~region_response_valid;
          #1; blocked(); tick();
          check(capture_state === BITS'(word),"hold preserves inactive owner/invalid/pending despite traffic");
        end
        @(negedge clock); region_request_ready='1; region_response_valid='1;
        restore_hold=0;
        #1;
        if ((word & 1)!=0) begin
          check(!request_ready && region_request_valid=='0 && response_valid,"restored pending blocks new request");
          if ((word & 2)!=0)
            check(response_error && response_data==0 && region_response_ready=='0,"restored invalid response has no endpoint");
          else begin
            check(region_response_ready == ({{(N-1){1'b0}},1'b1} << (word>>2)),"only original endpoint acknowledges response");
            check(response_data==64'hcafe0000+(word>>2) && response_error==((word>>2)%2),"exact restored response payload/error");
          end
        end else
          check(request_ready && region_request_valid[N-1] && !response_valid,"inactive restored payload allows new request");
        tick(); acks++;
        request_valid=0; response_ready=0; snapshots++;
      end
    end
    $fclose(fd); check(snapshots==5,"all donor words independently restored");
    // Exhaust the complete representable owner state, including every inactive
    // owner bit and invalid flag. These are ABI fixtures, separate from donor
    // snapshots; they establish no CPU or hardware-capture acceptance.
    for(integer k=0; k<N*4; k++) begin
      @(negedge clock); restore_hold=1; restore_load=1; restore_state=BITS'(k);
      request_valid=0; response_ready=1;
      #1; check(!restore_error,"all bounded owner encodings admitted under hold"); blocked();
      tick(); restore_load=0;
      check(capture_state===BITS'(k),"every complete state encoding read back under hold");
      @(negedge clock); #1; blocked(); tick();
      check(capture_state===BITS'(k),"every state encoding held with ready endpoints");
      @(negedge clock); restore_hold=0;
      #1;
      if ((k & 1)!=0) begin
        check(response_valid && !request_ready,"exhaustive pending response continuation");
        if ((k & 2)!=0)
          check(response_data==0 && response_error && region_response_ready=='0,"exhaustive invalid continuation");
        else
          check(response_data==64'hcafe0000+(k>>2) && response_error==((k>>2)%2) &&
            region_response_ready==({{(N-1){1'b0}},1'b1} << (k>>2)),"exhaustive owner response continuation");
      end else
        check(!response_valid && request_ready && response_data==0,"exhaustive inactive continuation");
      tick(); check(capture_state===BITS'(k & ~1),"only pending changes when response drains");
      encodings++;
    end
    // All representable invalid owner codes reject, even with pending clear.
    for(integer k=N; k<(1<<OW); k++) begin
      @(negedge clock); restore_hold=1; restore_load=1; restore_state=BITS'(k*4);
      word=int'(capture_state); #1;
      check(restore_error,"out-of-range inactive owner rejected"); blocked(); tick();
      check(capture_state===BITS'(word),"invalid load cannot partially mutate owner");
    end
    @(negedge clock); restore_hold=0; restore_load=1; restore_state=0;
    request_valid=1; response_ready=1; word=int'(capture_state); #1;
    check(restore_error,"load without held destination rejected"); blocked(); tick();
    check(capture_state===BITS'(word),"unheld load leaves complete state untouched");
    // Reset dominates restore, while every handshake remains blocked.
    @(negedge clock); restore_hold=1; restore_load=1; reset=1;
    #1; blocked(); tick(); check(capture_state===BITS'(0),"shared reset cancels restored outstanding owner");
  endtask
  initial begin
    $dumpfile("router-restore.vcd"); $dumpvars(0,region_router_restore_tb);
    check($value$plusargs("mode=%s",mode) && $value$plusargs("image=%s",path),"explicit mode and image required");
    for(integer k=0;k<N;k++) begin
      region_response_data[k*64 +: 64]=64'hcafe0000+k;
      region_response_error[k]=k%2;
    end
    repeat(2) tick();
    @(negedge clock); reset=0;
    if (!ENABLED) begin restore_hold=1'bx; restore_load=1'bx; restore_state='x; end
    if (mode=="source") donor(); else begin check(ENABLED,"destination requires opt-in"); destination(); end
    $display("ROUTER_RESTORE_PASS regions=%0d enabled=%0d mode=%s checks=%0d snapshots=%0d blocked_edges=%0d acknowledged_edges=%0d encodings=%0d",N,ENABLED,mode,checks,snapshots,blocked_edges,acks,encodings);
    $finish;
  end
  initial begin #1000000; check(0,"watchdog"); end
endmodule
