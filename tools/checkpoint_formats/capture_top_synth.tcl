# Native localhost Vivado only. This is FPGATop with generated fixture storage,
# an existing diagnostic bridge stream and the actual CPU DMA engine. It is
# not the Rocket recipe, a routed FPGA image, or hardware capture evidence.
set generated_dir [file normalize [lindex $argv 0]]
set output_dir [file normalize [lindex $argv 1]]
foreach directory [list $generated_dir $output_dir] {
    if {[string first "/automations/checkpoint_loop/runs/" "$directory/"] < 0} {
        error "Generated inputs and synthesis outputs must be beneath checkpoint_loop/runs"
    }
}
file mkdir $output_dir
set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
foreach name {FPGATop.v generated-bank.sv CheckpointCaptureTransport.sv CheckpointCaptureCut.sv} {
    read_verilog -sv $generated_dir/$name
}
set stub_path $output_dir/fixture-clock-sink.v
set stub [open $stub_path w]
puts $stub {module TargetBox(input hostClock,input hostReset,input clock_valid,input clock_bits,output clock_ready);
  assign clock_ready=1'b1;
endmodule}
close $stub
read_verilog $stub_path
synth_design -top FPGATop -part xcvu47p-fsvh2892-2-e -mode out_of_context
create_clock -period 7.142857 [get_ports clock]
opt_design
report_utilization -file $output_dir/utilization.rpt
report_timing_summary -file $output_dir/timing.rpt
write_checkpoint -force $output_dir/FPGATop.dcp
puts "CHECKPOINT_TOP_SYNTH_PASS top=FPGATop scope=generated-storage-fixture-only"
close_project
