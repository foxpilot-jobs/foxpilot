#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/apps/web"

if ! node -e 'const [major, minor] = process.versions.node.split(".").map(Number); process.exit(major > 22 || (major === 22 && minor >= 18) ? 0 : 1)'; then
  printf 'Node 22.18+ is required. Found: %s\n' "$(node --version)" >&2
  exit 1
fi

# Environment-level npm settings take precedence over .npmrc, so force the
# public registry for reproducible open-source installs.
NPM_CONFIG_REGISTRY=https://registry.npmjs.org/ \
npm install --registry=https://registry.npmjs.org/

printf '\nWeb dependencies ready. Start the frontend with:\n  npm run dev\n'
