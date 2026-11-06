#!/usr/bin/env bash
# Run before every push: the same checks the Space build depends on. Stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== pytest";        .venv/bin/pytest -q
echo "== web tests";     (cd web && npm test --silent)
echo "== web build";     (cd web && npm run build --silent)
echo "== e2e (demo path, 360 and 1280 px)"; (cd web && npx playwright test --reporter=dot)
echo "== docker build";  docker build -q -t darby . >/dev/null
echo "== no tokens staged"
if git diff --cached | grep -E "hf_[A-Za-z0-9]{20,}" >/dev/null; then echo "a token is staged: stop"; exit 1; fi
echo "GATES GREEN"
