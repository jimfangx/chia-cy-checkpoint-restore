# Native localhost storage component, not a Rocket FPGA image or hardware capture.
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
# Resolve the unchanged relative readmem filenames against this private snapshot.
cd $generated_dir
read_verilog -sv generated-bank.sv
synth_design -top InitializedStorage -part xcvu47p-fsvh2892-2-e -mode out_of_context
create_clock -period 7.142857 [get_ports clock]
opt_design
report_utilization -file $output_dir/utilization.rpt
report_timing_summary -file $output_dir/timing.rpt
write_checkpoint -force $output_dir/InitializedStorage.dcp
write_verilog -force -mode funcsim $output_dir/native-functional.v
# Retain actual memory primitive INIT parameters for independent image checks.
set report [open $output_dir/initialization.rpt w]
set memories [get_cells -hier -filter {REF_NAME =~ RAM* || REF_NAME =~ URAM*}]
if {[llength $memories] == 0} { error "Synthesized RAM primitives and initialization must remain visible" }
foreach cell [lsort $memories] {
    puts $report "CELL $cell REF_NAME=[get_property REF_NAME $cell]"
    foreach property [lsort [list_property $cell]] {
        if {[string match INIT* $property]} { puts $report "$property=[get_property $property $cell]" }
    }
}
close $report
puts "INITIALIZED_BANK_SYNTH_PASS scope=generated-storage-component-only"
close_project
