#!/usr/bin/env bash
set -euo pipefail
JASPER_LIMITS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/python3 "$JASPER_LIMITS_DIR/jasper_limits.py" run -- \
    "${CHECKPOINT_JASPER_BIN:-/ecad/tools/cadence/JASPER/jasper_2025.03/bin/jg}" "$@"
