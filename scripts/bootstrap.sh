#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON_BIN:-python3}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  printf 'Python executable not found: %s\n' "$python_bin" >&2
  exit 1
fi

"$python_bin" -m venv .venv

# Keep installation independent from machine-level package indexes.
PIP_INDEX_URL=https://pypi.org/simple \
PIP_EXTRA_INDEX_URL= \
.venv/bin/python -m pip install --upgrade pip

PIP_INDEX_URL=https://pypi.org/simple \
PIP_EXTRA_INDEX_URL= \
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r requirements.txt

PIP_INDEX_URL=https://pypi.org/simple \
PIP_EXTRA_INDEX_URL= \
.venv/bin/python -m pip install --index-url https://pypi.org/simple --editable ".[dev,api]"

.venv/bin/python -m playwright install chromium

printf '\nEnvironment ready. Activate it with:\n  source .venv/bin/activate\n'
