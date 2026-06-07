#!/usr/bin/env bash
set -euo pipefail
# Activate the shared WSL2 venv (see ../../docs/setup.md).
source "${SPEECHRL_VENV:-$HOME/.venvs/speechrl}/bin/activate"
cd "$(dirname "$0")/.."
python -m omni_embedding_rl.main "$@"
