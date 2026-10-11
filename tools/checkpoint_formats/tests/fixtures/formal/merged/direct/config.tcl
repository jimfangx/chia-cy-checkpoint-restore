# Candidate polarity for the audited CKDFF positive-output model.
# No functional assumptions: verify must prove every state and output point.
set checkpoint_candidate_polarity -noninverted

# Symmetric equivalence: one gate reference matches each original RTL alias.
set checkpoint_gate_reference 1
set checkpoint_candidate_aliases [dict create {held_copy_reg[0]} {{held_copy_reg[0]} {held_reg[0]}} {held_copy_reg[1]} {{held_copy_reg[1]} {held_reg[1]}} {held_copy_reg[2]} {{held_copy_reg[2]} {held_reg[2]}} {held_copy_reg[3]} {{held_copy_reg[3]} {held_reg[3]}}]
