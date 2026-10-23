# Native localhost Vivado only. These generated components are not an F2 image.
set bank_dir [file normalize [lindex $argv 0]]
set widget_dir [file normalize [lindex $argv 1]]
set output_dir [file normalize [lindex $argv 2]]
foreach directory [list $bank_dir $widget_dir $output_dir] {
    if {[string first "/automations/checkpoint_loop/runs/" "$directory/"] < 0} {
        error "Generated input/output directories must be beneath checkpoint_loop/runs"
    }
}
file mkdir $output_dir
set_param general.maxThreads 4

proc synth_component {name top sources output_dir} {
    create_project -in_memory -part xcvu47p-fsvh2892-2-e
    foreach source $sources { read_verilog -sv $source }
    synth_design -top $top -part xcvu47p-fsvh2892-2-e -mode out_of_context
    create_clock -period 7.142857 [get_ports clock]
    opt_design
    set result_dir $output_dir/$name
    file mkdir $result_dir
    report_utilization -file $result_dir/utilization.rpt
    report_timing_summary -file $result_dir/timing.rpt
    write_checkpoint -force $result_dir/$top.dcp
    puts "CHECKPOINT_GENERATED_SYNTH_PASS component=$name top=$top"
    close_project
}

synth_component bank Harness [list $bank_dir/generated-bank.sv] $output_dir
synth_component widget CheckpointCaptureWidget [list \
    $widget_dir/widget/CheckpointCaptureWidget.v \
    $widget_dir/widget/CheckpointCaptureTransport.sv \
    $widget_dir/widget/CheckpointCaptureCut.sv] $output_dir
