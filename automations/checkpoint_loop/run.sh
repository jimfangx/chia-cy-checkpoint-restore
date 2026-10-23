#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/env.sh"
source "$ROOT_DIR/sims/firesim/env.sh"
# This host manages AWS F2. VCS and its licenses stay on EDA; f2.py sources
# sourceme-manager.sh only for manager-side commands.
set -u

# The Chia checkout is a sibling of this Chipyard checkout on this machine.
# Override CHIA_SOURCE if it is installed elsewhere.
CHIA_SOURCE="${CHIA_SOURCE:-$ROOT_DIR/../chia-cy-checkpoint-restore-chia}"
export PYTHONPATH="$CHIA_SOURCE${PYTHONPATH:+:$PYTHONPATH}"
python -c 'from chia.base.ChiaFunction import ChiaFunction' >/dev/null

exec python "$ROOT_DIR/automations/checkpoint_loop/loop.py" "$@"
