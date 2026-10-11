# Run in an isolated directory with CHECKPOINT_FIXTURE pointing to this directory.
# The test library has artificial timing/area; this is functional validation only.
set fixture $env(CHECKPOINT_FIXTURE)
set library $env(CHECKPOINT_LIBRARY)
set input_paths [list rtl [file join $fixture dut.v] library $library synthesis_script [info script]]
set input_hashes [dict create]
foreach {role path} $input_paths {
  dict set input_hashes $role [lindex [exec sha256sum $path] 0]
}
set_db library $library
read_hdl [file join $fixture dut.v]
elaborate StateMapDUT
set_db [get_db designs StateMapDUT] .retime false
create_clock -name clock -period 10 [get_db ports clock]
syn_generic
syn_map
syn_opt
# Exercise actual synthesis register cloning, not a rewritten emitted netlist.
# The resulting netlist hash and complete formal inventory bind this option.
if {[info exists env(CHECKPOINT_DUPLICATE_REGISTERS)] && $env(CHECKPOINT_DUPLICATE_REGISTERS) eq "1"} {
  set candidates [get_db insts -if {.name == *count_reg*}]
  if {[llength $candidates] != 4} {error "Expected four original counter flops"}
  duplicate_register $candidates -num_copies 2 -verbose
}
# A nontrivial bit-index permutation of synthesized scalar storage destinations.
# Rename native database objects while retaining their actual D/Q connectivity;
# the emitted successful netlist is never rewritten. This exercises reordered
# indexed destinations, not packed multibit cells or retimed state.
if {[info exists env(CHECKPOINT_REORDER_REGISTERS)] && $env(CHECKPOINT_REORDER_REGISTERS) eq "1"} {
  set slots {2 0 3 1}
  set candidates [get_db insts -if {.name == *count_reg*}]
  set renamed 0
  foreach inst $candidates {
    set old [get_db $inst .base_name]
    if {![regexp {^count_reg\[([0-3])\](_SYNTHESIS_SEQ_DUP_[0-9]+)?$} $old -> bit suffix]} {
      error "Unexpected counter storage name: $old"
    }
    set new [format {gate_count_reg[%d]%s} [lindex $slots $bit] $suffix]
    rename_obj $inst $new
    if {[get_db $inst .base_name] ne $new} {error "Native register rename failed"}
    puts "CHECKPOINT_REORDER\t$old\t$new"
    incr renamed
  }
  if {$renamed != 4 && $renamed != 8} {error "Incomplete counter destination permutation"}
}
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
