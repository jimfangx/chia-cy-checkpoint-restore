// Component owner only: endpoint response payloads and the global cut are external.
module physical_router_restore_tb;
  import "DPI-C" function void checkpoint_widget_failed();
  localparam integer ENTRIES=`ENTRIES, GATES=`GATES, ENABLED=`RESTORE_ENABLED;
  reg clock=0, reset=1;
  always #5 clock=~clock;
  reg [31:0] descriptor_entry=0;
  wire descriptor_valid;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth, functional_descriptor_entry, ce_descriptor_entry;
  reg functional_descriptor_valid=1, ce_descriptor_valid=1;
  reg [7:0] functional_descriptor_bank=2, ce_descriptor_bank=255;
  reg [15:0] functional_descriptor_slot=7, functional_descriptor_width=32;
  reg [15:0] ce_descriptor_slot=0, ce_descriptor_width=1;
  reg [31:0] functional_descriptor_depth=8, ce_descriptor_depth=1;
  reg request_valid=0, response_ready=0;
  wire request_ready, response_valid, response_error;
  reg [7:0] bank=2;
  reg [15:0] slot=7;
  reg [31:0] address=3;
  wire [63:0] response_data;
  wire functional_request_valid, ce_request_valid;
  reg functional_request_ready=1, ce_request_ready=1;
  wire [7:0] endpoint_bank;
  wire [15:0] endpoint_slot;
  wire [31:0] endpoint_address;
  reg functional_response_valid=1, ce_response_valid=1;
  wire functional_response_ready, ce_response_ready;
  reg [63:0] functional_response_data=64'h0123456789abcdef, ce_response_data=64'hfedcba9876543210;
  reg functional_response_error=0, ce_response_error=1;
  reg restore_hold=0, restore_load=0;
  reg [1:0] restore_state=0;
  wire [1:0] capture_state;
  wire restore_error;
  integer checks=0, snapshots=0, acks=0, encodings=0, blocked_edges=0;
  integer fd, code, word, corrupt_bit=-1;
  string mode, path;
  CheckpointPhysicalStateRouter #(.ENTRIES(ENTRIES), .GATES(GATES), .RESTORE_SUPPORTED(ENABLED)) dut(.*);
  task check(input bit ok, input string why);
    checks++;
    if (!ok) begin
      $display("PHYSICAL_RESTORE_FAIL mode=%s checks=%0d %s",mode,checks,why);
      checkpoint_widget_failed(); $finish;
    end
  endtask
  task tick; @(posedge clock); #1; endtask
  task blocked;
    check({request_ready,response_valid,functional_request_valid,ce_request_valid,
      functional_response_ready,ce_response_ready} === '0,"every handshake blocked before edge");
    check(response_data===64'd0 && response_error===1'b0,"blocked response has no payload/error");
    blocked_edges++;
  endtask
  task save_word(input integer expected);
    check(capture_state===2'(expected),"independent donor ABI oracle");
    $fdisplay(fd,"%x",capture_state); snapshots++;
  endtask
  task donor;
    fd=$fopen(path,"w"); check(fd!=0,"open donor image"); save_word(0);
    for(integer k=0;k<2;k++) begin
      @(negedge clock); bank=k ? 255 : 2; request_valid=1;
      #1; check(request_ready && functional_request_valid==!k && ce_request_valid==k,
        "one endpoint accepts donor request"); tick(); request_valid=0;
      @(negedge clock); bank=k ? 2 : 255; slot=65535; address=32'hffffffff;
      repeat(3) begin
        tick(); check(response_valid && !request_ready &&
          response_data==(k ? ce_response_data : functional_response_data) && response_error==k,
          "accepted endpoint survives selector changes and backpressure");
      end
      save_word(k*2+1);
      @(negedge clock); response_ready=1;
      tick(); response_ready=0; save_word(k*2);
    end
    $fclose(fd); check(snapshots==5,"all actual active and inactive source states");
  endtask
  task continuation(input integer value);
    if (value & 1) begin
      check(!request_ready && !functional_request_valid && !ce_request_valid,
        "restored outstanding request cannot be replaced");
      check(response_valid && response_error==(value>>1) &&
        response_data==((value>>1) ? ce_response_data : functional_response_data),
        "restored original response payload and error");
      check(functional_response_ready==!(value>>1) && ce_response_ready==(value>>1),
        "only the original endpoint may acknowledge");
    end else check(request_ready && !response_valid && !functional_response_ready && !ce_response_ready,
      "inactive selection retained without unsolicited response");
  endtask
  task destination;
    fd=$fopen(path,"r"); check(fd!=0,"open independent donor image");
    while (!$feof(fd)) begin
      code=$fscanf(fd,"%x\n",word);
      if (code==1) begin
        @(negedge clock); restore_hold=1; restore_load=1; restore_state=2'(word);
        if (corrupt_bit>=0) restore_state=restore_state ^ (2'b01<<corrupt_bit);
        request_valid=1; response_ready=1; bank=255;
        #1; blocked(); check(!restore_error,"bounded held load");
        tick(); restore_load=0;
        if (capture_state!==2'(word) && corrupt_bit>=0) begin
          blocked();
          $display("PHYSICAL_FIRST_DIVERGENCE signal=capture_state snapshot=%0d expected=%0h observed=%0h acknowledged_edges=%0d",snapshots,word,capture_state,acks);
          checkpoint_widget_failed(); $finish;
        end
        check(capture_state===2'(word),"complete readback before any acknowledged transaction edge");
        repeat(5) begin
          @(negedge clock); functional_request_ready=~functional_request_ready;
          ce_request_ready=~ce_request_ready;
          functional_response_valid=~functional_response_valid; ce_response_valid=~ce_response_valid;
          bank=~bank; slot=~slot; address=~address;
          #1; blocked(); tick(); check(capture_state===2'(word),"all original bits held during external traffic");
        end
        @(negedge clock); functional_request_ready=1; ce_request_ready=1;
        functional_response_valid=1; ce_response_valid=1; restore_hold=0; #1;
        continuation(word);
        tick(); acks++; request_valid=0; response_ready=0; snapshots++;
      end
    end
    $fclose(fd); check(snapshots==5,"five independently restored source states");
    for(integer k=0;k<4;k++) begin
      @(negedge clock); restore_hold=1; restore_load=1; restore_state=2'(k);
      request_valid=0; response_ready=1;
      #1; blocked(); check(!restore_error,"all four ABI encodings legal"); tick(); restore_load=0;
      check(capture_state===2'(k),"complete exhaustive ABI readback");
      @(negedge clock); #1; blocked(); tick(); check(capture_state===2'(k),"exhaustive held state");
      // Delay the selected endpoint while an unsolicited other response is valid.
      @(negedge clock); restore_hold=0;
      functional_response_valid=(k>>1); ce_response_valid=!(k>>1);
      #1; check(!response_valid && response_data==0 && !response_error,"selected delayed response stays pending");
      tick(); check(capture_state===2'(k),"unsolicited other endpoint cannot drain pending");
      @(negedge clock); functional_response_valid=1; ce_response_valid=1; #1; continuation(k);
      tick(); check(capture_state===2'(k & ~1),"only pending clears on response acknowledgement"); encodings++;
    end
    // An invalid unheld load cannot accept or drain a transaction or change state.
    for(integer k=0;k<4;k++) begin
      @(negedge clock); restore_hold=0; restore_load=1; restore_state=2'(k);
      request_valid=1; response_ready=1; word=int'(capture_state);
      #1; check(restore_error,"unheld load explicitly rejects"); blocked(); tick();
      check(capture_state===2'(word),"unheld load never partially changes state");
    end
    @(negedge clock); restore_hold=1; restore_load=1; restore_state=3; reset=1;
    #1; blocked(); tick(); check(capture_state===0,"common reset dominates complete restore");
  endtask
  initial begin
    $dumpfile("physical-restore.vcd"); $dumpvars(0,physical_router_restore_tb);
    check($value$plusargs("mode=%s",mode) && $value$plusargs("image=%s",path),"explicit mode/image");
    code=$value$plusargs("corrupt_bit=%d",corrupt_bit);
    repeat(2) tick(); @(negedge clock); reset=0;
    if (!ENABLED) begin restore_hold=1'bx; restore_load=1'bx; restore_state='x; end
    if (mode=="invalid") begin
      restore_hold=1; restore_load=1; restore_state=3; request_valid=1; response_ready=1;
      #1; check(restore_error && !descriptor_valid,"unsupported geometry cannot be restored"); blocked();
      repeat(3) begin tick(); check(capture_state===0,"invalid geometry retains original owner"); end
    end else if(mode=="source") donor();
    else begin check(ENABLED,"destination explicitly enabled"); destination(); end
    $display("PHYSICAL_RESTORE_PASS mode=%s checks=%0d snapshots=%0d encodings=%0d acknowledged_edges=%0d blocked_edges=%0d",mode,checks,snapshots,encodings,acks,blocked_edges);
    $finish;
  end
  initial begin #100000; check(0,"watchdog"); end
endmodule
