#!/usr/bin/env bash
set -euo pipefail
# Activate the shared Python environment (see docs/setup.md when available).
source "${SPEECHRL_VENV:-$HOME/.venvs/speechrl}/bin/activate"
cd "$(dirname "$0")/.."
python -m omni_embedding_rl.main "$@"
