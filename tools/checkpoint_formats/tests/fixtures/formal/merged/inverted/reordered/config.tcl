# Candidates for the same indexed permutation with inverted cell storage.
# Every state relation and output must pass without functional assumptions.
set checkpoint_candidate_polarity -inverted
set checkpoint_candidate_names [dict create \
  {gate_count_reg[2]} {count_reg[0]} \
  {gate_count_reg[0]} {count_reg[1]} \
  {gate_count_reg[3]} {count_reg[2]} \
  {gate_count_reg[1]} {count_reg[3]}]

# Symmetric equivalence: one gate reference matches each original RTL alias.
set checkpoint_gate_reference 1
set checkpoint_candidate_aliases [dict create {held_copy_reg[0]} {{held_copy_reg[0]} {held_reg[0]}} {held_copy_reg[1]} {{held_copy_reg[1]} {held_reg[1]}} {held_copy_reg[2]} {{held_copy_reg[2]} {held_reg[2]}} {held_copy_reg[3]} {{held_copy_reg[3]} {held_reg[3]}}]
