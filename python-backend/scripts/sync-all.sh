#!/usr/bin/env bash
# sync-all.sh — ein Kommando syncet alle Python venvs in python-backend/
#
# Struktur:
# - python-backend/.venv           = Workspace (agent, bridge, voice, memory_engine, mock, ingestion)
# - python-backend/compute/.venv   = isoliert (fastapi==0.116.1 Konflikt)
# - python-backend/kg_pipeline/.venv = isoliert (torch==2.3.1 hart)
# - python-backend/extraction_layout/.venv = isoliert (pillow<11 Konflikt)
# - python-backend/litellm-gateway/.venv = isoliert (transitive uvicorn<0.22 Konflikt)
# - python-backend/rust_core       = maturin-build, separat (via cargo/maturin, nicht uv sync)
#
# Siehe matrix/specs/18-python-backend-workspace-refactor.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

info() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*"; }

info "Workspace-Root sync (agent + bridge + voice + memory_engine + mock + ingestion)"
uv sync
ok "python-backend/.venv (shared)"

# Isolierte Subpakete — parallel via Background-Subshells
for sub in compute kg_pipeline extraction_layout litellm-gateway; do
  if [ -f "$ROOT/$sub/pyproject.toml" ]; then
    info "Isolated sync: $sub"
    (cd "$ROOT/$sub" && uv sync) &
  else
    warn "$sub/pyproject.toml missing, skipping"
  fi
done

wait
ok "Alle isolierten Subpakete synced"

info "rust_core build (maturin via cargo)"
if [ -f "$ROOT/rust_core/Cargo.toml" ]; then
  (cd "$ROOT/rust_core" && cargo build --release) &
  RUST_PID=$!
  wait "$RUST_PID"
  ok "rust_core/target/release/ built"
else
  warn "rust_core/Cargo.toml missing"
fi

info "Status-Übersicht"
for v in . compute kg_pipeline extraction_layout litellm-gateway; do
  if [ -d "$ROOT/$v/.venv" ]; then
    sz=$(du -sh "$ROOT/$v/.venv" 2>/dev/null | awk '{print $1}')
    printf '  ✓ %-22s %s\n' "$v/.venv" "$sz"
  else
    printf '  ✗ %-22s (missing)\n' "$v/.venv"
  fi
done
