# Explicit preserved physical macro architecture, no automatic RAM inference.
# Artificial cells/models; this validates functional state, not ASIC power.
set input_paths [list rtl $env(CHECKPOINT_RTL) implementation_rtl $env(CHECKPOINT_IMPLEMENTATION_RTL) macro_stub $env(CHECKPOINT_MACRO_STUB) library $env(CHECKPOINT_LIBRARY) synthesis_script [info script]]
set hashes [dict create]
foreach {role path} $input_paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
set_db library $env(CHECKPOINT_LIBRARY)
read_hdl $env(CHECKPOINT_MACRO_STUB)
read_hdl $env(CHECKPOINT_IMPLEMENTATION_RTL)
elaborate StateMapDUT
set_db [get_db hinsts -if {.base_name == memory}] .preserve true
set_db [get_db designs StateMapDUT] .retime false
create_clock -name clock -period 10 [get_db ports clock]
syn_generic
syn_map
syn_opt
write_hdl -depth 0 > netlist.v
report_gates > gates.rpt
foreach {role path} $input_paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Synthesis input changed: $role"}
  puts "CHECKPOINT_SYNTH_INPUT\t$role\t$digest"
}
puts "CHECKPOINT_SYNTH_OUTPUT\t[lindex [exec sha256sum netlist.v] 0]"
puts "CHECKPOINT_RETIMING=[get_db [get_db designs StateMapDUT] .retime]"
exit
