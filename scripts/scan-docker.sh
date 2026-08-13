#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! curl --fail --silent http://localhost:11435/api/tags >/dev/null; then
  printf 'Host Ollama is not reachable at http://localhost:11435.\n' >&2
  printf 'Start it with: OLLAMA_HOST=0.0.0.0:11435 ollama serve\n' >&2
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://foxpilot:foxpilot-dev-only@localhost:5432/foxpilot}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11435}"

foxpilot_bin="${FOXPILOT_BIN:-$repo_root/.venv/bin/foxpilot}"
if [[ ! -x "$foxpilot_bin" ]]; then
  printf 'FoxPilot CLI not found at %s. Run ./scripts/bootstrap.sh first.\n' "$foxpilot_bin" >&2
  exit 1
fi

if ! curl --fail --silent http://localhost:8000/api/v1/health/ready >/dev/null; then
  printf 'FoxPilot API is not ready at http://localhost:8000.\n' >&2
  printf 'Start Docker services with: docker compose up -d\n' >&2
  exit 1
fi

exec "$foxpilot_bin" scan "$@"
