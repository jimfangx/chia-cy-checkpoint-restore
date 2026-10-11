# Formality P-2019.03-SP2 adapter. Only final passing compare points are evidence.
# Keep raw human reports beside the machine export for independent inspection.
set input_paths [list rtl $env(CHECKPOINT_RTL) models $env(CHECKPOINT_CELLS) netlist $env(CHECKPOINT_NETLIST) formal_script [info script] formal_configuration $env(CHECKPOINT_FORMAL_CONFIG)]
set input_hashes [dict create]
foreach {role path} $input_paths {
  dict set input_hashes $role [lindex [exec sha256sum $path] 0]
}
source $env(CHECKPOINT_FORMAL_CONFIG)
if {$checkpoint_candidate_polarity ni {-inverted -noninverted}} {error "Unsupported candidate match configuration"}
read_verilog -r $env(CHECKPOINT_RTL)
set_top r:/WORK/StateMapDUT
read_verilog -i $env(CHECKPOINT_CELLS)
read_verilog -i $env(CHECKPOINT_NETLIST)
set_top i:/WORK/StateMapDUT
# Automatic inversion matching in this release can swap same-width registers.
# Supply exact-name candidates from the actual inventories, with a build-bound
# polarity hypothesis. Every candidate relation and all outputs must verify.
# These are proof partitions, never passing-state evidence or reset assumptions.
current_design r:/WORK/StateMapDUT
set reference_registers [dict create]
foreach_in_collection reg [all_registers -cells] {
  dict set reference_registers [get_attribute $reg full_name] 1
}
current_design i:/WORK/StateMapDUT
foreach_in_collection reg [all_registers -cells] {
  set checkpoint_impl [get_attribute $reg full_name]
  if {[regexp {^i:/WORK/StateMapDUT/(.+)/state_reg$} $checkpoint_impl -> name]} {
    set checkpoint_ref r:/WORK/StateMapDUT/$name
    if {[dict exists $reference_registers $checkpoint_ref]} {
      set_user_match -type cell $checkpoint_candidate_polarity $checkpoint_ref $checkpoint_impl
    }
  }
}
match
set passed [verify]
redirect matched.rpt {report_matched_points}
redirect passing.rpt {report_passing_points}
redirect passing-noninverted.rpt {report_passing_points -point_type reg -status noninverted}
redirect passing-inverted.rpt {report_passing_points -point_type reg -status inverted}
redirect unmatched.rpt {report_unmatched_points}
redirect failing.rpt {report_failing_points}
redirect aborted.rpt {report_aborted_points}
redirect unverified.rpt {report_unverified_points}
redirect blackboxes.rpt {report_black_boxes}
set out [open evidence.tsv w]
puts $out "FORMAT\tformality-state-v1"
puts $out "VERIFY\t$passed"
foreach {role path} $input_paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $input_hashes $role]} {error "Formal input changed during proof: $role"}
  puts $out "INPUT\t$role\t$digest"
}
foreach side {r i} {
  current_design $side:/WORK/StateMapDUT
  foreach_in_collection reg [all_registers -cells] {
    puts $out "REGISTER\t$side\t[get_attribute $reg full_name]"
  }
}
foreach polarity {noninverted inverted} {
  foreach pair [report_passing_points -point_type reg -status $polarity -list] {
    puts $out "PROVEN\t$polarity\t[join $pair \t]"
  }
}
puts $out "END"
close $out
exit
