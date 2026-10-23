# Native localhost component synthesis, not a Rocket image or physical capture.
set generated_dir [file normalize [lindex $argv 0]]
set output_dir [file normalize [lindex $argv 1]]
foreach directory [list $generated_dir $output_dir] {
    if {[string first "/automations/checkpoint_loop/runs/" "$directory/"] < 0} {
        error "All inputs and evidence must be beneath checkpoint_loop/runs"
    }
}
file mkdir $output_dir
set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog -sv $generated_dir/generated-bank.sv
synth_design -top SyncStorage -part xcvu47p-fsvh2892-2-e -mode out_of_context
create_clock -period 7.142857 [get_ports clock]
opt_design
report_utilization -file $output_dir/utilization.rpt
report_timing_summary -file $output_dir/timing.rpt
write_checkpoint -force $output_dir/SyncStorage.dcp
puts "SYNCHRONOUS_BANK_SYNTH_PASS scope=generated-storage-component-only"
close_project
