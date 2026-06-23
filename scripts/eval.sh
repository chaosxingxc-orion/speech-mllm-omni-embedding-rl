#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${SPEECHRL_VENV:-}" ]]; then
  source "${SPEECHRL_VENV}/bin/activate"
fi
python -m omni_embedding_rl.main mode=eval "$@"
