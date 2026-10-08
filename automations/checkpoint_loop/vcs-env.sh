#!/usr/bin/env bash
# Source after Chipyard/FireSim env.sh or any login-shell tool setup.
CHECKPOINT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKPOINT_LICENSE_SETUP="${CHECKPOINT_LICENSE_SETUP:-$HOME/flexlm.sh}"
if [[ -f "$CHECKPOINT_LICENSE_SETUP" ]]; then
    source "$CHECKPOINT_LICENSE_SETUP"
fi

# An absolute bin/vcs path still honors VCS_HOME; keep both on this release.
export VCS_HOME=/ecad/tools/synopsys/vcs/Y-2026.03-SP1
export VCS_64=1
export PATH="$VCS_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CHECKPOINT_ROOT/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
