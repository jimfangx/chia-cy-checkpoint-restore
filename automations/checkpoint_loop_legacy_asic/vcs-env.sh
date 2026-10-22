#!/usr/bin/env bash
# Source after Chipyard/FireSim env.sh or any login-shell tool setup.
CHECKPOINT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKPOINT_LICENSE_SETUP="${CHECKPOINT_LICENSE_SETUP:-/ecad/tools/vlsi.bashrc}"
if [[ -f "$CHECKPOINT_LICENSE_SETUP" ]]; then
    source "$CHECKPOINT_LICENSE_SETUP"
fi

# An absolute bin/vcs path still honors VCS_HOME; keep both on this release.
export VCS_HOME=/ecad/tools/synopsys/vcs/Y-2026.03-SP1
export VCS_64=1
export CHECKPOINT_JASPER_MEMORY_GB="${CHECKPOINT_JASPER_MEMORY_GB:-475}"
export CHECKPOINT_JASPER_TIMEOUT_SECONDS="${CHECKPOINT_JASPER_TIMEOUT_SECONDS:-0}"
# GCC 14+ rejects implicit declarations in VCS-generated C. Keep Conda's
# Python on PATH, but route VCS's internal gcc calls through system GCC 13.
export CC=/usr/bin/gcc-13
export CXX=/usr/bin/g++-13
export VCS_CC="$CC"
export PATH="$VCS_HOME/bin:$CHECKPOINT_ROOT/automations/checkpoint_loop/compiler-bin:$PATH"
export LD_LIBRARY_PATH="$CHECKPOINT_ROOT/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
