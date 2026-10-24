  wire [31:0] functional_descriptor_entry, ce_descriptor_entry;
  wire functional_descriptor_valid=functional_descriptor_entry<2;
  wire [7:0] functional_descriptor_bank=functional_descriptor_entry+1;
  wire [15:0] functional_descriptor_slot=0;
  wire [15:0] functional_descriptor_width=functional_descriptor_entry==0 ? 64 : 32;
  wire [31:0] functional_descriptor_depth=functional_descriptor_entry==0 ? 1 : 3;
  wire ce_descriptor_valid;
  wire [7:0] ce_descriptor_bank;
  wire [15:0] ce_descriptor_slot, ce_descriptor_width;
  wire [31:0] ce_descriptor_depth;
  wire functional_request_valid, ce_request_valid, ce_request_ready;
  wire functional_response_ready, ce_response_ready, ce_response_valid, ce_response_error;
  wire [63:0] ce_response_data;
  CheckpointPhysicalStateRouter #(.ENTRIES(2),.GATES(3)) router(
    .request_valid(bank_request_valid),.request_ready(bank_request_ready),
    .response_valid(bank_response_valid),.response_ready(bank_response_ready),
    .response_data(bank_response_data),.response_error(bank_response_error),
    .endpoint_bank(),.endpoint_slot(),.endpoint_address(),.*);
  `CE_BANK_MODULE ce_endpoint(
    .read_enable(physical_read_enable),.descriptor_entry(ce_descriptor_entry),
    .descriptor_valid(ce_descriptor_valid),.descriptor_bank(ce_descriptor_bank),
    .descriptor_slot(ce_descriptor_slot),.descriptor_width(ce_descriptor_width),
    .descriptor_depth(ce_descriptor_depth),.request_valid(ce_request_valid),
    .request_ready(ce_request_ready),.response_valid(ce_response_valid),
    .response_ready(ce_response_ready),.response_data(ce_response_data),
    .response_error(ce_response_error),.*);
