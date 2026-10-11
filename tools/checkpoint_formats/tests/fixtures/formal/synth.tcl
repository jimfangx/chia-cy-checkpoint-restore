# Run in an isolated directory with CHECKPOINT_FIXTURE pointing to this directory.
# The test library has artificial timing/area; this is functional validation only.
set fixture $env(CHECKPOINT_FIXTURE)
set input_paths [list rtl [file join $fixture dut.v] library [file join $fixture cells.lib] synthesis_script [info script]]
set input_hashes [dict create]
foreach {role path} $input_paths {
  dict set input_hashes $role [lindex [exec sha256sum $path] 0]
}
set_db library [file join $fixture cells.lib]
read_hdl [file join $fixture dut.v]
elaborate StateMapDUT
set_db [get_db designs StateMapDUT] .retime false
create_clock -name clock -period 10 [get_db ports clock]
syn_generic
syn_map
syn_opt
write_hdl > netlist.v
report_gates > gates.rpt
foreach {role path} $input_paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $input_hashes $role]} {error "Synthesis input changed during build: $role"}
  puts "CHECKPOINT_SYNTH_INPUT\t$role\t$digest"
}
puts "CHECKPOINT_SYNTH_OUTPUT\t[lindex [exec sha256sum netlist.v] 0]"
puts "CHECKPOINT_RETIMING=[get_db [get_db designs StateMapDUT] .retime]"
exit
