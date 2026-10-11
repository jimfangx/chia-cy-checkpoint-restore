# Complete selected pre-FAME DUT with explicit preserved functional RAMs.
# Empty synthesis stubs never serve as formal or simulation models. A successful
# synthesis is not a complete state correspondence proof and cannot permit load.
set input_paths [list rtl $env(CHECKPOINT_RTL) architecture $env(CHECKPOINT_ARCHITECTURE) memory_stubs $env(CHECKPOINT_MEMORY_STUBS) memory_models $env(CHECKPOINT_MEMORY_MODELS) candidate $env(CHECKPOINT_ARCHITECTURE_CANDIDATE) library $env(CHECKPOINT_LIBRARY) synthesis_script [info script]]
set hashes [dict create]
foreach {role path} $input_paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
set_db library $env(CHECKPOINT_LIBRARY)
read_hdl $env(CHECKPOINT_MEMORY_STUBS)
read_hdl -sv $env(CHECKPOINT_ARCHITECTURE)
elaborate $env(CHECKPOINT_TOP)
set_db [get_db designs] .retime false
set memories [get_db hinsts -if {.base_name == ckmem_*}]
if {[llength $memories] != $env(CHECKPOINT_MEMORY_INSTANCES)} {error "Incomplete production memory hierarchy"}
set_db $memories .preserve true
foreach memory $memories {puts "CHECKPOINT_PRESERVED_MEMORY\t[get_db $memory .name]"}
create_clock -name clock -period 10 [get_db ports clock]
syn_generic
syn_map
syn_opt
write_hdl > netlist.v
report_gates > gates.rpt
report_area > area.rpt
foreach {role path} $input_paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Synthesis input changed: $role"}
  puts "CHECKPOINT_SYNTH_INPUT\t$role\t$digest"
}
foreach design [get_db designs] {
  if {[get_db $design .retime] ne "false"} {error "Production retiming was enabled"}
  puts "CHECKPOINT_RETIMING\t[get_db $design .name]\t[get_db $design .retime]"
}
puts "CHECKPOINT_SYNTH_OUTPUT\t[lindex [exec sha256sum netlist.v] 0]"
puts "CHECKPOINT_SYNTHESIS_ONLY_UNPROVEN_STATE_MAP"
exit
