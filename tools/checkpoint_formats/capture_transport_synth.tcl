# Native localhost Vivado only. Out-of-context component, not an F2 image.
set output_dir [file normalize [lindex $argv 0]]
if {$output_dir eq "" || [string first "/automations/checkpoint_loop/runs/" "$output_dir/"] < 0} {
    error "Supply an output directory beneath checkpoint_loop/runs"
}
file mkdir $output_dir
set_param general.maxThreads 4
read_verilog -sv sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv
read_verilog -sv sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv
synth_design -top CheckpointCaptureTransport -part xcvu47p-fsvh2892-2-e -mode out_of_context \
    -generic [list OWNERS=16 ENTRIES=1024 "MANIFEST_SHA256=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"]
create_clock -period 7.142857 [get_ports clock]
opt_design
report_utilization -file $output_dir/utilization.rpt
report_timing_summary -file $output_dir/timing.rpt
write_checkpoint -force $output_dir/CheckpointCaptureTransport.dcp
puts "CHECKPOINT_TRANSPORT_SYNTH_PASS"
