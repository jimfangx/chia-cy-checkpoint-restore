#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/env.sh"
source "$ROOT_DIR/sims/firesim/env.sh"
set -u

# VCS's 64-bit executable needs libelf from this checkout's conda environment.
export LD_LIBRARY_PATH="$ROOT_DIR/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# The Chia checkout is a sibling of this Chipyard checkout on this machine.
# Override CHIA_SOURCE if it is installed elsewhere.
CHIA_SOURCE="${CHIA_SOURCE:-$ROOT_DIR/../chia-cy-checkpoint-restore-chia}"
export PYTHONPATH="$CHIA_SOURCE${PYTHONPATH:+:$PYTHONPATH}"
python -c 'from chia.base.ChiaFunction import ChiaFunction' >/dev/null

exec python "$ROOT_DIR/tools/checkpoint_loop/loop.py" "$@"
