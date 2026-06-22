#!/usr/bin/env bash
set -euo pipefail
source "${SPEECHRL_VENV:-$HOME/.venvs/speechrl}/bin/activate"
cd "$(dirname "$0")/.."
# mode is already defined by the experiment config (global), so override it (no leading +).
python -m omni_embedding_rl.main mode=eval "$@"
