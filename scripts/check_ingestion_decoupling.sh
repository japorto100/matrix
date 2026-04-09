#!/usr/bin/env bash
# exec-15 D17 Decoupling Verification.
#
# Ensures that ingestion/, kg_pipeline/, and retrieval/ never import from agent/.
# Returns 0 if clean, 1 if any forbidden import found.

set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
PB="$REPO_ROOT/python-backend"

declare -i errors=0

check() {
  local pkg="$1"
  echo "=== checking $pkg/ ==="
  if [ ! -d "$PB/$pkg" ]; then
    echo "  (no $pkg/ — skipping)"
    return
  fi
  # Match: from agent... | import agent... but NOT agent.control which is OK at the proxy boundary
  if grep -rEn "^[[:space:]]*(from agent\.|import agent\.|from agent import|import agent$)" \
        --include="*.py" "$PB/$pkg" 2>/dev/null; then
    echo "  ERROR: $pkg/ imports from agent.* (D17 violation)"
    errors=$((errors + 1))
  else
    echo "  ok — no agent.* imports"
  fi

  # Also ensure no cross-package imports between the three siblings
  for other in ingestion kg_pipeline retrieval; do
    if [ "$other" = "$pkg" ]; then continue; fi
    if grep -rEn "^[[:space:]]*(from $other\.|import $other\.|from $other import|import $other$)" \
          --include="*.py" "$PB/$pkg" 2>/dev/null; then
      echo "  ERROR: $pkg/ imports from $other/ (D17 violation)"
      errors=$((errors + 1))
    fi
  done
}

check ingestion
check kg_pipeline
check retrieval

if [ "$errors" -gt 0 ]; then
  echo ""
  echo "FAIL: $errors decoupling violation(s) found"
  exit 1
fi

echo ""
echo "PASS: all packages clean (D17 satisfied)"
