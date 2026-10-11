# Candidates for native Genus indexed scalar-destination permutation.
# These are hypotheses, not reset/input assumptions or proof evidence.
set checkpoint_candidate_polarity -noninverted
set checkpoint_candidate_names [dict create \
  {gate_count_reg[2]} {count_reg[0]} \
  {gate_count_reg[0]} {count_reg[1]} \
  {gate_count_reg[3]} {count_reg[2]} \
  {gate_count_reg[1]} {count_reg[3]}]
