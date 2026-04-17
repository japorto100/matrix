#!/usr/bin/env bash
# dev-stack.sh — Matrix Dev Stack (Linux / podman port of dev-stack3.ps1)
#
# Architektur (wie dev-stack3.ps1):
#   - Infra via podman-compose: tuwunel, nats, postgres, optional seaweedfs
#   - Backend lokal (nicht containerisiert): go-appservice, python agent, bridge
#   - Frontends lokal: nextjs-chat, control-ui, agent-chat, frontend_merger
#
# Usage:
#   ./scripts/dev-stack.sh                    # Full stack
#   ./scripts/dev-stack.sh --tuwunel16        # Tuwunel v1.6.0-rc image
#   ./scripts/dev-stack.sh --frontend-only    # Nur alle 4 Frontends
#   ./scripts/dev-stack.sh --merger-only      # Nur frontend_merger :3003
#   ./scripts/dev-stack.sh --skip-python      # Ohne Python Services
#   ./scripts/dev-stack.sh --kill             # Alles stoppen und raus

set -u
set -o pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs/devstack"
PID_DIR="${REPO_ROOT}/logs/devstack/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

# ─── Flags ──────────────────────────────────────────────────────────────────
SKIP_HOMESERVER=false
SKIP_NATS=false
SKIP_POSTGRES=false
SKIP_STORAGE=true            # seaweedfs optional
SKIP_OBSERVABILITY=true      # openobserve optional
SKIP_GO=false
SKIP_PYTHON=false
SKIP_AGENT_SERVICE=false
SKIP_INGESTION=false
SKIP_LITELLM=true            # nicht Teil vom Default
SKIP_BRIDGE=false
USE_MOCK=false
SKIP_FRONTEND=false
SKIP_NEXTJS=false
SKIP_CONTROL_UI=false
SKIP_AGENT_CHAT=false
SKIP_MERGER=false
TUWUNEL16=true               # default: v1.6 (wie vom User gewuenscht)
FRONTEND_ONLY=false
AGENT_ONLY=false
MERGER_ONLY=false
KILL_MODE=false

for arg in "$@"; do
  case "$arg" in
    --skip-homeserver)    SKIP_HOMESERVER=true ;;
    --skip-nats)          SKIP_NATS=true ;;
    --skip-postgres)      SKIP_POSTGRES=true ;;
    --with-storage)       SKIP_STORAGE=false ;;
    --with-observability) SKIP_OBSERVABILITY=false ;;
    --skip-go)            SKIP_GO=true ;;
    --skip-python)        SKIP_PYTHON=true ;;
    --skip-agent)         SKIP_AGENT_SERVICE=true ;;
    --skip-ingestion)     SKIP_INGESTION=true ;;
    --with-litellm)       SKIP_LITELLM=false ;;
    --skip-bridge)        SKIP_BRIDGE=true ;;
    --mock)               USE_MOCK=true ;;
    --skip-frontend)      SKIP_FRONTEND=true ;;
    --skip-nextjs)        SKIP_NEXTJS=true ;;
    --skip-control-ui)    SKIP_CONTROL_UI=true ;;
    --skip-agent-chat)    SKIP_AGENT_CHAT=true ;;
    --skip-merger)        SKIP_MERGER=true ;;
    --tuwunel16)          TUWUNEL16=true ;;
    --tuwunel15)          TUWUNEL16=false ;;
    --frontend-only)      FRONTEND_ONLY=true ;;
    --agent-only)         AGENT_ONLY=true ;;
    --merger-only)        MERGER_ONLY=true ;;
    --kill)               KILL_MODE=true ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

if $FRONTEND_ONLY; then
  SKIP_HOMESERVER=true; SKIP_NATS=true; SKIP_POSTGRES=true
  SKIP_GO=true; SKIP_PYTHON=true; SKIP_BRIDGE=true; SKIP_AGENT_SERVICE=true
fi
if $AGENT_ONLY; then
  SKIP_HOMESERVER=true; SKIP_NATS=true; SKIP_POSTGRES=true
  SKIP_NEXTJS=true; SKIP_CONTROL_UI=true; SKIP_MERGER=true
fi
if $MERGER_ONLY; then
  SKIP_HOMESERVER=true; SKIP_NATS=true; SKIP_POSTGRES=true
  SKIP_GO=true; SKIP_PYTHON=true; SKIP_BRIDGE=true; SKIP_AGENT_SERVICE=true
  SKIP_NEXTJS=true; SKIP_CONTROL_UI=true; SKIP_AGENT_CHAT=true
fi

# ─── Ports (muessen matchen mit .env.example und docker-compose.yml) ───────
PORT_TUWUNEL=8448
PORT_NATS=4222
PORT_POSTGRES=5433
PORT_GO=8090
PORT_AGENT=8094
PORT_BRIDGE=8097
PORT_INGESTION=8098
PORT_LITELLM=4000
PORT_NEXTJS=3000
PORT_CONTROL_UI=3001
PORT_AGENT_CHAT=3002
PORT_MERGER=3003
PORT_LIVEKIT=7880
PORT_SEAWEED_S3=8333
PORT_OPENOBSERVE=5080

ALL_PORTS=($PORT_TUWUNEL $PORT_NATS $PORT_POSTGRES $PORT_GO $PORT_AGENT $PORT_BRIDGE \
           $PORT_INGESTION $PORT_LITELLM $PORT_NEXTJS $PORT_CONTROL_UI $PORT_AGENT_CHAT \
           $PORT_MERGER $PORT_LIVEKIT $PORT_SEAWEED_S3 $PORT_OPENOBSERVE)

# ─── Helpers ────────────────────────────────────────────────────────────────
log()  { printf "\033[36m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
warn() { printf "\033[33m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
die()  { printf "\033[31m[%s] ERROR: %s\033[0m\n" "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

wait_for_port() {
  local port=$1 name=${2:-:$1} timeout=${3:-30}
  local i=0
  while [ $i -lt $timeout ]; do
    if nc -z 127.0.0.1 "$port" 2>/dev/null; then
      log "✓ $name up on :$port"
      return 0
    fi
    sleep 1; i=$((i+1))
  done
  warn "timeout waiting for $name on :$port"
  return 1
}

kill_port() {
  local port=$1 name=${2:-:$1}
  local pids
  pids=$(lsof -t -i :"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
    sleep 1
    pids=$(lsof -t -i :"$port" -sTCP:LISTEN 2>/dev/null || true)
    [ -n "$pids" ] && echo "$pids" | xargs -r kill -KILL 2>/dev/null || true
    log "killed $name (:$port)"
  fi
}

spawn() {
  # spawn <name> <cwd> <cmd...>
  local name=$1 cwd=$2; shift 2
  local logfile="$LOG_DIR/${name}.log"
  local pidfile="$PID_DIR/${name}.pid"
  log "spawning $name (cwd=$cwd)"
  (
    cd "$cwd" || exit 1
    exec "$@"
  ) >"$logfile" 2>&1 &
  echo $! > "$pidfile"
  log "  pid=$(cat "$pidfile")  log=$logfile"
}

# ─── KILL MODE ──────────────────────────────────────────────────────────────
if $KILL_MODE; then
  log "Stopping Matrix DevStack…"
  for p in "${ALL_PORTS[@]}"; do kill_port "$p"; done
  if have podman-compose; then
    (cd "$REPO_ROOT" && podman-compose down 2>/dev/null || true)
  elif have docker-compose; then
    (cd "$REPO_ROOT" && docker-compose down 2>/dev/null || true)
  fi
  rm -f "$PID_DIR"/*.pid 2>/dev/null
  log "Done."
  exit 0
fi

# ─── Preflight ──────────────────────────────────────────────────────────────
log "DevStack starting in $REPO_ROOT"
log "Log dir:  $LOG_DIR"
log "Tuwunel:  $([ "$TUWUNEL16" = "true" ] && echo 'v1.6.0 image' || echo 'stable image')"

COMPOSE=""
if have podman-compose; then COMPOSE="podman-compose"
elif have docker-compose;  then COMPOSE="docker-compose"
fi

# ─── Infrastructure via compose (tuwunel, nats, postgres) ──────────────────
if [ -n "$COMPOSE" ] && ! $SKIP_HOMESERVER && ! $SKIP_NATS && ! $SKIP_POSTGRES; then
  log "Starting infra via $COMPOSE: tuwunel + nats + postgres"
  (cd "$REPO_ROOT" && $COMPOSE up -d tuwunel nats postgres 2>&1) \
    | tee -a "$LOG_DIR/compose.log" || warn "compose up failed — Images evt nicht gezogen?"
  wait_for_port $PORT_TUWUNEL "tuwunel" 45 || true
  wait_for_port $PORT_NATS "nats" 20 || true
  wait_for_port $PORT_POSTGRES "postgres" 30 || true
else
  warn "compose tool nicht gefunden oder infra-skipped — bitte manuell starten"
fi

# ─── Go Appservice (local process) ─────────────────────────────────────────
if ! $SKIP_GO; then
  if [ -f "$REPO_ROOT/go-appservice/.env.development" ]; then
    spawn "go-appservice" "$REPO_ROOT/go-appservice" \
      env GO_ENV=development bash -c 'go run ./cmd/appservice'
  else
    warn "go-appservice/.env.development fehlt — cp .env.example .env.development"
  fi
fi

# ─── Python agent service (:8094) ──────────────────────────────────────────
if ! $SKIP_PYTHON && ! $SKIP_AGENT_SERVICE; then
  if $USE_MOCK; then
    spawn "python-agent" "$REPO_ROOT/python-backend" python -m mock.mock_agent
  else
    spawn "python-agent" "$REPO_ROOT/python-backend" \
      python -m uvicorn agent.app:app --host 127.0.0.1 --port "$PORT_AGENT" --reload
  fi
fi

# ─── Python bridge (:8097) ─────────────────────────────────────────────────
if ! $SKIP_PYTHON && ! $SKIP_BRIDGE; then
  spawn "python-bridge" "$REPO_ROOT/python-backend" \
    python -m bridge.app
fi

# ─── Python ingestion worker (:8098) ───────────────────────────────────────
if ! $SKIP_PYTHON && ! $SKIP_INGESTION; then
  spawn "python-ingestion" "$REPO_ROOT/python-backend" \
    python -m ingestion.worker
fi

# ─── LiteLLM Gateway (:4000) — opt-in ──────────────────────────────────────
if ! $SKIP_LITELLM; then
  spawn "litellm" "$REPO_ROOT/python-backend" \
    python -m litellm --config ./config.yaml --port $PORT_LITELLM
fi

# ─── Frontends ──────────────────────────────────────────────────────────────
if ! $SKIP_FRONTEND; then
  if ! $SKIP_NEXTJS;     then spawn "nextjs-chat"    "$REPO_ROOT/nextjs-chat"    bun run dev; fi
  if ! $SKIP_CONTROL_UI; then spawn "control-ui"     "$REPO_ROOT/control-ui"     bun run dev; fi
  if ! $SKIP_AGENT_CHAT; then spawn "agent-chat"     "$REPO_ROOT/agent-chat"     bun run dev; fi
  if ! $SKIP_MERGER;     then spawn "frontend-merger" "$REPO_ROOT/frontend_merger" bun run dev; fi
fi

# ─── Ready Report ──────────────────────────────────────────────────────────
sleep 3
log ""
log "─── Stack Status ──────────────────────────────────────────"
declare -A PORT_LABEL=(
  [$PORT_TUWUNEL]="tuwunel (Matrix homeserver)"
  [$PORT_NATS]="nats"
  [$PORT_POSTGRES]="postgres"
  [$PORT_GO]="go-appservice"
  [$PORT_AGENT]="python-agent"
  [$PORT_BRIDGE]="python-bridge"
  [$PORT_INGESTION]="python-ingestion"
  [$PORT_LITELLM]="litellm"
  [$PORT_NEXTJS]="nextjs-chat"
  [$PORT_CONTROL_UI]="control-ui"
  [$PORT_AGENT_CHAT]="agent-chat"
  [$PORT_MERGER]="frontend-merger"
)
for p in "${!PORT_LABEL[@]}"; do
  if nc -z 127.0.0.1 "$p" 2>/dev/null; then
    printf "  \033[32m✓\033[0m :%-5s  %s\n" "$p" "${PORT_LABEL[$p]}"
  fi
done
log ""
log "Tail all logs:  tail -F $LOG_DIR/*.log"
log "Stop stack:     $0 --kill"
