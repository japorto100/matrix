#!/usr/bin/env bash
# scheduler-e2e.sh — Run the exec-scheduler Phase-1 integration tests
# against a running dev-stack.
#
# Prereqs (one-shot setup):
#   ./scripts/dev-stack.sh              # infra + go-appservice + python
#   (wait for services healthy)
#
# Then:
#   ./scripts/scheduler-e2e.sh
#
# What this script does:
#   1. Probe Postgres :5433 + NATS :4222 + go-appservice :9000
#   2. Run alembic upgrade to 021_agent_metrics
#   3. Run pytest tests/e2e/test_scheduler_flow.py with RUN_INTEGRATION=1
#
# Bringing up ONLY the infra (without dev-stack.sh's full local-services
# setup):
#   podman-compose up -d nats postgres tuwunel
#   cd python-backend && .venv/bin/python -m alembic upgrade head
#   # then start go-appservice + python-backend manually, or use dev-stack.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# ─── Probes ─────────────────────────────────────────────────────────────────
probe() {
	local name=$1 host=$2 port=$3
	if ! timeout 2 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
		echo "❌ $name not reachable at $host:$port"
		return 1
	fi
	echo "✅ $name up ($host:$port)"
}

echo "── Stack probe ──────────────────────────────────────"
probe postgres       localhost 5433 || {
	echo "Start with: podman-compose up -d postgres"
	exit 1
}
probe nats           localhost 4222 || {
	echo "Start with: podman-compose up -d nats"
	exit 1
}
probe go-appservice  localhost 9000 || {
	echo "Start with: ./scripts/dev-stack.sh  (or go run -tags goolm ./go-appservice/cmd/appservice)"
	exit 1
}

# ─── Migrations ─────────────────────────────────────────────────────────────
echo ""
echo "── Running Alembic migrations ───────────────────────"
cd "$REPO_ROOT/python-backend"
if [[ ! -f .venv/bin/python ]]; then
	echo "python-backend/.venv missing — run: cd python-backend && uv sync"
	exit 1
fi
.venv/bin/python -m alembic upgrade head

# ─── E2E tests ──────────────────────────────────────────────────────────────
echo ""
echo "── E2E tests ────────────────────────────────────────"
export RUN_INTEGRATION=1
export HINDSIGHT_DB_URL="${HINDSIGHT_DB_URL:-postgresql://postgres:postgres@localhost:5433/hindsight_dev}"
export NATS_URL="${NATS_URL:-nats://localhost:4222}"
export GO_APPSERVICE_URL="${GO_APPSERVICE_URL:-http://localhost:9000}"

.venv/bin/python -m pytest tests/e2e/test_scheduler_flow.py -v -m integration "$@"
