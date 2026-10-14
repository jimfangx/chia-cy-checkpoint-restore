# Evidence and loop-controller checkpoints

Iteration 84's returned audit failed after the controller created its next
checkpoint: the audit required the pre-checkpoint Git index bytes and HEAD.
The implementation turn had preserved them, but they are deliberately changed
by the controller between turns. The original report and failure log remain
under `automations/checkpoint_loop/runs/`; no historical evidence was rewritten.

Iteration 85 separates these checks:

- Reusable evidence checks bind protected plan/environment/PDF bytes, exact
  current implementation and native build inputs, all retained raw traces and
  readbacks, actual process results, generated inventory and regression scope.
  Recorded controller checkpoints must remain ancestors of the local history.
  Protected plans must remain unstaged.
- Agent-turn checks additionally require the original raw index bytes and
  HEADs immediately before returning. They are recorded under `runs/` and are
  deliberately excluded from the reusable verification commands.
- Retained historical runs are labeled historical. When an implementation
  input has changed, its old bytes must match both an archived source snapshot
  and the exact Git object in a pinned controller revision. This establishes
  historical provenance, not a current-source test result. Current native
  evidence independently binds and tests the current implementation.

The concrete checks are `runs/m11-iteration85/verify-evidence.py`,
`verify-retained-evidence.py`, `retained-source-bindings.json`,
`protected-inputs.json` and `verify-protected-turn.py`. The reusable check is:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration85.verify-evidence
```

An unsupported CPU owner or incomplete semantic inventory still rejects.
Evidence bookkeeping does not grant checkpoint support or replace the native
fresh-process continuation and ordinary RTL replay required for M11.
