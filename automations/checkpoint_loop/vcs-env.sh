#!/usr/bin/env bash
# EDA only. Source LAST after the cluster's native build environment. Licenses
# are inherited from the login shell; never reset them to the old /ecad servers.
CHECKPOINT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKPOINT_VCS="${CHECKPOINT_EDA_VCS:-/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs}"
if [[ ! -x "$CHECKPOINT_VCS" ]]; then
    echo "VCS is unavailable here: $CHECKPOINT_VCS. Run checks with automations/checkpoint_loop/eda.py." >&2
    return 1
fi
export VCS_HOME="$(cd "$(dirname "$CHECKPOINT_VCS")/.." && pwd)"
export VCS_64=1

checkpoint_native_compiler() {
    local candidate
    while IFS= read -r candidate; do
        if [[ "$candidate" != "$CHECKPOINT_ROOT/automations/checkpoint_loop/compiler-bin/"* ]]; then
            printf '%s\n' "$candidate"
            return
        fi
    done < <(type -aP "$1")
    return 1
}

# Prefer GCC 13 (including Rocky's gcc-toolset layout). Allow an explicit
# native EDA compiler without assuming Ubuntu's /usr/bin/g++-13 exists.
if [[ -n "${CHECKPOINT_EDA_CC:-}" ]]; then
    export CC="$CHECKPOINT_EDA_CC"
elif [[ -x /usr/bin/gcc-13 ]]; then
    export CC=/usr/bin/gcc-13
elif [[ -x /opt/rh/gcc-toolset-13/root/usr/bin/gcc ]]; then
    export CC=/opt/rh/gcc-toolset-13/root/usr/bin/gcc
else
    export CC="$(checkpoint_native_compiler gcc)"
fi
if [[ -n "${CHECKPOINT_EDA_CXX:-}" ]]; then
    export CXX="$CHECKPOINT_EDA_CXX"
elif [[ -x /usr/bin/g++-13 ]]; then
    export CXX=/usr/bin/g++-13
elif [[ -x /opt/rh/gcc-toolset-13/root/usr/bin/g++ ]]; then
    export CXX=/opt/rh/gcc-toolset-13/root/usr/bin/g++
else
    export CXX="$(checkpoint_native_compiler g++)"
fi
if [[ ! -x "$CC" || ! -x "$CXX" ]]; then
    echo "Missing EDA C/C++ compiler; configure CHECKPOINT_EDA_CC/CXX in the remote setup." >&2
    return 1
fi
export VCS_CC="$CC"
export CHECKPOINT_EDA_VCS="$CHECKPOINT_VCS"
export CHECKPOINT_EDA_CC="$CC"
export CHECKPOINT_EDA_CXX="$CXX"
export PATH="$VCS_HOME/bin:$CHECKPOINT_ROOT/automations/checkpoint_loop/compiler-bin:$PATH"
if [[ -d "$CHECKPOINT_ROOT/.conda-env/lib" ]]; then
    export LD_LIBRARY_PATH="$CHECKPOINT_ROOT/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
