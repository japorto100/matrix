#!/usr/bin/env bash
# dev-stack.sh — Matrix Dev Stack (Linux / podman, SOTA 2026-04)
#
# Philosophie: Default-OFF + explicit opt-in. Additiv. Script kann während
# laufendem Stack erneut aufgerufen werden um einzelne Services hinzu-/weg-
# zuschalten — kein automatisches Herunterfahren.
#
# Architektur:
#   Compose (image):   tuwunel, nats, postgres, garage/seaweedfs, litellm,
#                      livekit+lk-jwt+coturn, cloudflared, openobserve, etc.
#   Lokal (unser code): go-appservice, python-agent, python-bridge,
#                       python-ingestion, frontend_merger
#
# ──────────────────────────────────────────────────────────────────────────
# USAGE
#
#   ./scripts/dev-stack.sh [flags]
#
# PRESETS (sparen Tipparbeit):
#   --matrix-core    infra + go + bridge + agent + frontend   (text-chat, kein LLM)
#   --matrix-chat    matrix-core + litellm                    (echte Agent-Replies)
#   --matrix-full    matrix-chat + calls                      (alle Gates außer Tunnel)
#   --matrix-mobile  matrix-full + tunnel                     (Mobile external)
#   --matrix-mock    matrix-core + llm-mock + mock-agent      (UI-tests ohne API-Keys)
#   --agent-dev      nats + postgres + litellm + agent + bridge (ohne Matrix)
#   --memory-dev     postgres + falkordb + agent              (exec-memory)
#   --sandbox-dev    postgres + sandbox + agent               (exec-12)
#
# INFRA (compose, opt-in):
#   --tuwunel                    Matrix Homeserver (Default v1.5.2)
#   --tuwunel16                  Tuwunel v1.6.0-rc image
#   --nats                       Message Bus
#   --postgres                   DB + pgvector
#   --storage=garage|seaweedfs   Storage-Backend (Default: garage)
#   --storage=off                kein S3 (tuwunel local-media)
#   --litellm                    LLM Gateway (Port 4000)
#   --llm-mock                   Mock-LLM-Server
#   --sandbox                    OpenSandbox Pair (exec-12)
#   --calls                      livekit + lk-jwt + coturn
#   --tunnel                     cloudflared quick (trycloudflare.com)
#   --tunnel-named               cloudflared named (braucht Token in .env)
#   --observability              openobserve + otel-collector + postgres-exporter
#   --valkey                     Redis-fork Cache
#   --pgbouncer                  Postgres connection pooler
#   --falkordb                   KG-Backend A (exec-memory)
#   --nornic                     KG-Backend B (exec-memory)
#
# LOKAL (unser Code, opt-in):
#   --go                         go-appservice :8090
#   --agent                      python-agent :8094
#   --bridge                     python-bridge :8097
#   --ingestion                  python-ingestion :8098
#   --frontend                   frontend_merger :3003
#   --mock-agent                 python-agent als mock.mock_agent
#
# OVERRIDES (kombinierbar mit Presets):
#   --skip=<service>[,<service>...]   entferne aus Preset
#     (z.B. --matrix-full --skip=ingestion,falkordb)
#
# OPERATIONS:
#   --kill                       alles stoppen (compose down + lokale pids)
#   --kill=<service>             nur diesen stoppen
#   --restart=<service>          stop + start <service>
#   --status                     zeige welche services laufen (kein start)
#   --help, -h                   diese Usage
#
# BEISPIELE:
#   ./scripts/dev-stack.sh --matrix-chat          # Phase 1: Agent-Mention tests
#   ./scripts/dev-stack.sh --matrix-full          # Phase 2: + Calls
#   ./scripts/dev-stack.sh --matrix-chat --tunnel # + Mobile-remote
#   ./scripts/dev-stack.sh --calls                # füge calls zum laufenden hinzu
#   ./scripts/dev-stack.sh --kill=livekit         # nur livekit stoppen
#   ./scripts/dev-stack.sh --status               # was läuft?

set -u
set -o pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs/devstack"
PID_DIR="${REPO_ROOT}/logs/devstack/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

# ─── Default: alles OFF ───────────────────────────────────────────────────────
# Compose services
WANT_TUWUNEL=false
TUWUNEL_IMAGE_TAG="v1.6.0"   # stable seit 2026-04-12, default
WANT_NATS=false
WANT_POSTGRES=false
STORAGE_BACKEND="off"     # off | garage | seaweedfs
WANT_LITELLM=false
WANT_LLM_MOCK=false
WANT_SANDBOX=false
WANT_CALLS=false
WANT_TUNNEL=false
WANT_TUNNEL_NAMED=false
WANT_OBSERVABILITY=false
WANT_VALKEY=false
WANT_PGBOUNCER=false
WANT_FALKORDB=false
WANT_NORNIC=false

# Local services
WANT_GO=false
WANT_AGENT=false
WANT_BRIDGE=false
WANT_INGESTION=false
WANT_FRONTEND=false
USE_MOCK_AGENT=false

# Operations
KILL_MODE=false
KILL_TARGET=""
RESTART_TARGET=""
STATUS_MODE=false

# Skip list (from --skip=x,y,z)
SKIP_LIST=""

show_help() { sed -n '2,78p' "$0"; exit 0; }

# Preset expansions — werden auf die WANT_* flags gemapped
apply_preset_matrix_core() {
  WANT_TUWUNEL=true; WANT_NATS=true; WANT_POSTGRES=true
  STORAGE_BACKEND="garage"
  WANT_GO=true; WANT_AGENT=true; WANT_BRIDGE=true; WANT_FRONTEND=true
}
apply_preset_matrix_chat() {
  apply_preset_matrix_core
  WANT_LITELLM=true
}
apply_preset_matrix_full() {
  apply_preset_matrix_chat
  WANT_CALLS=true
}
apply_preset_matrix_mobile() {
  apply_preset_matrix_full
  WANT_TUNNEL=true
}
apply_preset_matrix_mock() {
  apply_preset_matrix_core
  WANT_LLM_MOCK=true
  USE_MOCK_AGENT=true
}
apply_preset_agent_dev() {
  WANT_NATS=true; WANT_POSTGRES=true
  WANT_LITELLM=true
  WANT_AGENT=true; WANT_BRIDGE=true
}
apply_preset_memory_dev() {
  WANT_POSTGRES=true; WANT_FALKORDB=true
  WANT_AGENT=true
}
apply_preset_sandbox_dev() {
  WANT_POSTGRES=true; WANT_SANDBOX=true
  WANT_AGENT=true
}

# ─── Flag parsing ────────────────────────────────────────────────────────────
if [ $# -eq 0 ]; then show_help; fi

for arg in "$@"; do
  case "$arg" in
    # Presets
    --matrix-core)     apply_preset_matrix_core ;;
    --matrix-chat)     apply_preset_matrix_chat ;;
    --matrix-full)     apply_preset_matrix_full ;;
    --matrix-mobile)   apply_preset_matrix_mobile ;;
    --matrix-mock)     apply_preset_matrix_mock ;;
    --agent-dev)       apply_preset_agent_dev ;;
    --memory-dev)      apply_preset_memory_dev ;;
    --sandbox-dev)     apply_preset_sandbox_dev ;;

    # Infra compose
    --tuwunel)         WANT_TUWUNEL=true ;;
    --tuwunel16)       WANT_TUWUNEL=true ;;   # legacy no-op: v1.6.0 stable ist default
    --tuwunel15)       WANT_TUWUNEL=true; TUWUNEL_IMAGE_TAG="v1.5.1" ;;   # legacy fallback
    --nats)            WANT_NATS=true ;;
    --postgres)        WANT_POSTGRES=true ;;
    --storage=garage)    STORAGE_BACKEND="garage" ;;
    --storage=seaweedfs) STORAGE_BACKEND="seaweedfs" ;;
    --storage=off)       STORAGE_BACKEND="off" ;;
    --litellm)         WANT_LITELLM=true ;;
    --llm-mock)        WANT_LLM_MOCK=true ;;
    --sandbox)         WANT_SANDBOX=true ;;
    --calls)           WANT_CALLS=true ;;
    --tunnel)          WANT_TUNNEL=true ;;
    --tunnel-named)    WANT_TUNNEL_NAMED=true ;;
    --observability)   WANT_OBSERVABILITY=true ;;
    --valkey)          WANT_VALKEY=true ;;
    --pgbouncer)       WANT_PGBOUNCER=true ;;
    --falkordb)        WANT_FALKORDB=true ;;
    --nornic)          WANT_NORNIC=true ;;

    # Local processes
    --go)              WANT_GO=true ;;
    --agent)           WANT_AGENT=true ;;
    --bridge)          WANT_BRIDGE=true ;;
    --ingestion)       WANT_INGESTION=true ;;
    --frontend)        WANT_FRONTEND=true ;;
    --mock-agent)      USE_MOCK_AGENT=true; WANT_AGENT=true ;;

    # Overrides
    --skip=*)          SKIP_LIST="${arg#--skip=}" ;;

    # Operations
    --kill)            KILL_MODE=true ;;
    --kill=*)          KILL_TARGET="${arg#--kill=}" ;;
    --restart=*)       RESTART_TARGET="${arg#--restart=}" ;;
    --status)          STATUS_MODE=true ;;
    -h|--help)         show_help ;;

    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# Apply skip-list (comma separated)
if [ -n "$SKIP_LIST" ]; then
  IFS=',' read -ra SKIPS <<< "$SKIP_LIST"
  for svc in "${SKIPS[@]}"; do
    case "$svc" in
      tuwunel)        WANT_TUWUNEL=false ;;
      nats)           WANT_NATS=false ;;
      postgres)       WANT_POSTGRES=false ;;
      storage|garage|seaweedfs) STORAGE_BACKEND="off" ;;
      litellm)        WANT_LITELLM=false ;;
      llm-mock)       WANT_LLM_MOCK=false ;;
      sandbox)        WANT_SANDBOX=false ;;
      calls)          WANT_CALLS=false ;;
      tunnel)         WANT_TUNNEL=false ;;
      observability)  WANT_OBSERVABILITY=false ;;
      valkey)         WANT_VALKEY=false ;;
      pgbouncer)      WANT_PGBOUNCER=false ;;
      falkordb)       WANT_FALKORDB=false ;;
      nornic)         WANT_NORNIC=false ;;
      go)             WANT_GO=false ;;
      agent)          WANT_AGENT=false ;;
      bridge)         WANT_BRIDGE=false ;;
      ingestion)      WANT_INGESTION=false ;;
      frontend)       WANT_FRONTEND=false ;;
      *) echo "unknown skip target: $svc" >&2; exit 2 ;;
    esac
  done
fi

# ─── Ports ────────────────────────────────────────────────────────────────────
PORT_TUWUNEL=8448
PORT_NATS=4222
PORT_POSTGRES=5433
PORT_SEAWEED_S3=8333
PORT_GARAGE_S3=3900
PORT_LITELLM=4000
PORT_LLM_MOCK=8095
PORT_SANDBOX=8080
PORT_LIVEKIT=7880
PORT_LK_JWT=8082
PORT_COTURN=3478
PORT_OPENOBSERVE=5080
PORT_VALKEY=6379
PORT_PGBOUNCER=6432
PORT_FALKORDB=6380
PORT_NORNIC=7474
PORT_GO=29318   # MATRIX_APPSERVICE_PORT — callback-port für tuwunel, nicht 8090
PORT_AGENT=8094
PORT_BRIDGE=8097
PORT_INGESTION=8098
PORT_MERGER=3003

# ─── Helpers ──────────────────────────────────────────────────────────────────
log()  { printf "\033[36m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
ok()   { printf "\033[32m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
warn() { printf "\033[33m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
die()  { printf "\033[31m[%s] ERROR: %s\033[0m\n" "$(date +%H:%M:%S)" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

port_up() { nc -z 127.0.0.1 "$1" 2>/dev/null; }

wait_for_port() {
  local port=$1 name=${2:-:$1} timeout=${3:-30} i=0
  while [ $i -lt $timeout ]; do
    port_up "$port" && { ok "✓ $name :$port"; return 0; }
    sleep 1; i=$((i+1))
  done
  warn "timeout: $name :$port"; return 1
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
  # Skip if pidfile exists and process still alive
  if [ -f "$pidfile" ]; then
    local pid
    pid=$(cat "$pidfile" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      log "⧖  $name already running (pid=$pid)"
      return 0
    fi
  fi
  log "spawning $name (cwd=$cwd)"
  (
    cd "$cwd" || exit 1
    exec "$@"
  ) >"$logfile" 2>&1 &
  echo $! > "$pidfile"
  log "   pid=$(cat "$pidfile") log=$logfile"
}

# ─── COMPOSE tool detection ──────────────────────────────────────────────────
COMPOSE=""
if have podman-compose; then COMPOSE="podman-compose"
elif have docker-compose;  then COMPOSE="docker-compose"
fi

compose_up() {
  local services=("$@")
  [ ${#services[@]} -eq 0 ] && return 0
  [ -z "$COMPOSE" ] && { warn "compose tool fehlt — $* nicht gestartet"; return 1; }

  # Profile-Namen ableiten aus service-liste.
  # podman-compose <1.1 kennt kein --profile flag → wir nutzen COMPOSE_PROFILES
  # env-var (wird von podman-compose + docker-compose gleichermassen respektiert).
  local profiles_csv=""
  for s in "${services[@]}"; do
    local p=""
    case "$s" in
      litellm)                                       p="litellm" ;;
      opensandbox|opensandbox-server)                p="sandbox" ;;
      coturn|livekit-server|lk-jwt-service)          p="calls" ;;
      cloudflared)                                   p="tunnel" ;;
      cloudflared-named)                             p="tunnel-named" ;;
      openobserve|otel-collector|postgres-exporter)  p="observability" ;;
      valkey)                                        p="cache" ;;
      garage)                                        p="storage-garage" ;;
      falkordb)                                      p="kg-falkor" ;;
      nornic)                                        p="kg-nornic" ;;
      pgbouncer)                                     p="pooler" ;;
      llm-mock)                                      p="mock" ;;
    esac
    # Dedupe: skip wenn profile schon in der csv
    if [ -n "$p" ] && [[ ",$profiles_csv," != *",$p,"* ]]; then
      profiles_csv="${profiles_csv:+${profiles_csv},}$p"
    fi
  done

  # Split in zwei phasen: default-services (kein profile) und profile-services
  # getrennt aufrufen. Podman-compose mit COMPOSE_PROFILES=X skipped alle
  # default-services — daher erst default ohne env-var, dann profile-services mit.
  local default_svcs=() profile_svcs=()
  for s in "${services[@]}"; do
    case "$s" in
      tuwunel|nats|postgres) default_svcs+=("$s") ;;
      *) profile_svcs+=("$s") ;;
    esac
  done

  local common_env=(
    "TUWUNEL_IMAGE=ghcr.io/matrix-construct/tuwunel:${TUWUNEL_IMAGE_TAG}"
    "TUWUNEL_CONFIG=${TUWUNEL_CONFIG:-tuwunel.v1.6.toml}"
  )

  if [ ${#default_svcs[@]} -gt 0 ]; then
    log "compose up (default): ${default_svcs[*]}"
    (cd "$REPO_ROOT" && env "${common_env[@]}" $COMPOSE up -d "${default_svcs[@]}" 2>&1) \
      | tee -a "$LOG_DIR/compose.log" || warn "compose up (default) failed"
  fi

  if [ ${#profile_svcs[@]} -gt 0 ]; then
    log "compose up (profiles: $profiles_csv): ${profile_svcs[*]}"
    (cd "$REPO_ROOT" && env "${common_env[@]}" COMPOSE_PROFILES="$profiles_csv" \
      $COMPOSE up -d "${profile_svcs[@]}" 2>&1) \
      | tee -a "$LOG_DIR/compose.log" || warn "compose up (profiles) failed"
  fi
}

compose_stop() {
  local service=$1
  [ -z "$COMPOSE" ] && { warn "compose tool fehlt"; return 1; }
  log "compose stop: $service"
  (cd "$REPO_ROOT" && $COMPOSE stop "$service" 2>&1) \
    | tee -a "$LOG_DIR/compose.log" || warn "compose stop failed"
}

# ─── STATUS MODE ──────────────────────────────────────────────────────────────
if $STATUS_MODE; then
  log "─── Current Stack Status ─────────────────────────────────────────"
  declare -A SVC_PORT=(
    [tuwunel]=$PORT_TUWUNEL [nats]=$PORT_NATS [postgres]=$PORT_POSTGRES
    [seaweedfs]=$PORT_SEAWEED_S3 [garage]=$PORT_GARAGE_S3
    [litellm]=$PORT_LITELLM [llm-mock]=$PORT_LLM_MOCK
    [sandbox]=$PORT_SANDBOX [livekit]=$PORT_LIVEKIT [lk-jwt]=$PORT_LK_JWT
    [coturn]=$PORT_COTURN [openobserve]=$PORT_OPENOBSERVE
    [valkey]=$PORT_VALKEY [pgbouncer]=$PORT_PGBOUNCER
    [falkordb]=$PORT_FALKORDB [nornic]=$PORT_NORNIC
    [go-appservice]=$PORT_GO [python-agent]=$PORT_AGENT
    [python-bridge]=$PORT_BRIDGE [python-ingestion]=$PORT_INGESTION
    [frontend-merger]=$PORT_MERGER
  )
  for svc in "${!SVC_PORT[@]}"; do
    p=${SVC_PORT[$svc]}
    if port_up "$p"; then
      printf "  \033[32m✓\033[0m %-18s :%-5s\n" "$svc" "$p"
    fi
  done
  exit 0
fi

# ─── KILL MODE (all) ──────────────────────────────────────────────────────────
if $KILL_MODE; then
  log "Stopping ALL…"
  # Lokale pids first
  for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    local_pid=$(cat "$pidfile" 2>/dev/null || echo "")
    [ -n "$local_pid" ] && kill -TERM "$local_pid" 2>/dev/null && log "killed $(basename "${pidfile%.pid}") (pid=$local_pid)"
    rm -f "$pidfile"
  done
  # Ports mit stale listeners
  for p in $PORT_GO $PORT_AGENT $PORT_BRIDGE $PORT_INGESTION $PORT_MERGER; do kill_port "$p"; done
  # Compose down
  if [ -n "$COMPOSE" ]; then
    (cd "$REPO_ROOT" && $COMPOSE --profile litellm --profile sandbox --profile calls \
      --profile tunnel --profile tunnel-named --profile observability --profile cache \
      --profile storage-garage --profile kg-falkor --profile kg-nornic --profile pooler \
      --profile mock down 2>/dev/null || true)
  fi
  ok "Done."
  exit 0
fi

# ─── KILL SINGLE ──────────────────────────────────────────────────────────────
if [ -n "$KILL_TARGET" ]; then
  case "$KILL_TARGET" in
    go|go-appservice)   kill_port $PORT_GO "go-appservice"; rm -f "$PID_DIR/go-appservice.pid" ;;
    agent|python-agent) kill_port $PORT_AGENT "python-agent"; rm -f "$PID_DIR/python-agent.pid" ;;
    bridge|python-bridge) kill_port $PORT_BRIDGE "python-bridge"; rm -f "$PID_DIR/python-bridge.pid" ;;
    ingestion|python-ingestion) kill_port $PORT_INGESTION "python-ingestion"; rm -f "$PID_DIR/python-ingestion.pid" ;;
    frontend|frontend-merger) kill_port $PORT_MERGER "frontend"; rm -f "$PID_DIR/frontend-merger.pid" ;;
    # Compose services — nutze compose stop um cleanly herunterzufahren
    tuwunel|nats|postgres|seaweedfs|garage|litellm|llm-mock|coturn|livekit|lk-jwt|\
    livekit-server|lk-jwt-service|cloudflared|cloudflared-named|openobserve|\
    otel-collector|postgres-exporter|valkey|pgbouncer|falkordb|nornic|\
    opensandbox|opensandbox-server)
      # Map friendly → compose-name
      case "$KILL_TARGET" in
        livekit) compose_stop "livekit-server" ;;
        lk-jwt)  compose_stop "lk-jwt-service" ;;
        *)       compose_stop "$KILL_TARGET" ;;
      esac ;;
    *) die "unknown kill target: $KILL_TARGET" ;;
  esac
  exit 0
fi

# ─── RESTART SINGLE ───────────────────────────────────────────────────────────
if [ -n "$RESTART_TARGET" ]; then
  log "restart $RESTART_TARGET…"
  "$0" --kill="$RESTART_TARGET"
  sleep 2
  # Re-run with just the single --flag
  case "$RESTART_TARGET" in
    tuwunel)           exec "$0" --tuwunel ;;
    nats)              exec "$0" --nats ;;
    postgres)          exec "$0" --postgres ;;
    garage|seaweedfs)  exec "$0" --storage="$RESTART_TARGET" ;;
    litellm)           exec "$0" --litellm ;;
    llm-mock)          exec "$0" --llm-mock ;;
    sandbox)           exec "$0" --sandbox ;;
    calls|livekit|lk-jwt|coturn) exec "$0" --calls ;;
    go|go-appservice)  exec "$0" --go ;;
    agent|python-agent) exec "$0" --agent ;;
    bridge|python-bridge) exec "$0" --bridge ;;
    ingestion|python-ingestion) exec "$0" --ingestion ;;
    frontend|frontend-merger) exec "$0" --frontend ;;
    *) die "unknown restart target: $RESTART_TARGET" ;;
  esac
fi

# ─── START services (additiv) ────────────────────────────────────────────────
log "DevStack: additive start"

# Garage-Preflight: Wenn Tuwunel + Garage gewählt → prüfe ob Keys in tuwunel.v1.6.toml
# schon gesetzt sind (setup-garage.sh wurde gelaufen). Sonst würde Tuwunel beim
# startup_check=true crashen weil Placeholder-Keys ungültig sind.
if $WANT_TUWUNEL && [ "$STORAGE_BACKEND" = "garage" ]; then
  TUWUNEL_TOML="$REPO_ROOT/homeserver/tuwunel.v1.6.toml"
  if [ -f "$TUWUNEL_TOML" ] && grep -q "GARAGE_ACCESS_KEY_PLACEHOLDER\|GARAGE_SECRET_KEY_PLACEHOLDER" "$TUWUNEL_TOML"; then
    warn "Garage-keys sind noch Placeholder in tuwunel.v1.6.toml"
    warn "Erst setup laufen lassen:"
    warn "  ./scripts/setup-garage.sh"
    warn "Dann dev-stack erneut starten."
    die "abort: garage-setup muss einmalig gelaufen sein"
  fi
fi

# Tuwunel-Config-Datei für compose volume-mount (aktuell nur v1.6)
export TUWUNEL_CONFIG="tuwunel.v1.6.toml"
export TUWUNEL_IMAGE="ghcr.io/matrix-construct/tuwunel:${TUWUNEL_IMAGE_TAG}"

# Compose-services aus WANT-flags ableiten
COMPOSE_SVCS=()
$WANT_TUWUNEL       && COMPOSE_SVCS+=("tuwunel")
$WANT_NATS          && COMPOSE_SVCS+=("nats")
$WANT_POSTGRES      && COMPOSE_SVCS+=("postgres")
[ "$STORAGE_BACKEND" = "garage" ]    && COMPOSE_SVCS+=("garage")
[ "$STORAGE_BACKEND" = "seaweedfs" ] && COMPOSE_SVCS+=("seaweedfs")
$WANT_LITELLM       && COMPOSE_SVCS+=("litellm")
$WANT_LLM_MOCK      && COMPOSE_SVCS+=("llm-mock")
$WANT_SANDBOX       && COMPOSE_SVCS+=("opensandbox-server")
$WANT_CALLS         && COMPOSE_SVCS+=("livekit-server" "lk-jwt-service" "coturn")
$WANT_TUNNEL        && COMPOSE_SVCS+=("cloudflared")
$WANT_TUNNEL_NAMED  && COMPOSE_SVCS+=("cloudflared-named")
$WANT_OBSERVABILITY && COMPOSE_SVCS+=("openobserve" "otel-collector" "postgres-exporter")
$WANT_VALKEY        && COMPOSE_SVCS+=("valkey")
$WANT_PGBOUNCER     && COMPOSE_SVCS+=("pgbouncer")
$WANT_FALKORDB      && COMPOSE_SVCS+=("falkordb")
$WANT_NORNIC        && COMPOSE_SVCS+=("nornic")

if [ ${#COMPOSE_SVCS[@]} -gt 0 ]; then
  compose_up "${COMPOSE_SVCS[@]}"
  # Wait for critical ports
  $WANT_TUWUNEL  && wait_for_port $PORT_TUWUNEL "tuwunel" 60
  $WANT_NATS     && wait_for_port $PORT_NATS "nats" 20
  $WANT_POSTGRES && wait_for_port $PORT_POSTGRES "postgres" 30
  [ "$STORAGE_BACKEND" = "garage" ]    && wait_for_port $PORT_GARAGE_S3 "garage" 30
  [ "$STORAGE_BACKEND" = "seaweedfs" ] && wait_for_port $PORT_SEAWEED_S3 "seaweedfs" 30
  $WANT_LITELLM  && wait_for_port $PORT_LITELLM "litellm" 45
  $WANT_CALLS    && wait_for_port $PORT_LIVEKIT "livekit" 20
  $WANT_CALLS    && wait_for_port $PORT_LK_JWT "lk-jwt" 20
fi

# ─── Appservice Registration (idempotent, tuwunel v1.6.0 workaround) ────────
# Persistiert in tuwunel-DB — nur beim ersten-start / nach tuwunel-DB-wipe nötig.
# Auto-skip wenn namespace-test zeigt appservice schon registriert.
# Hintergrund siehe scripts/devstack.md §"Appservice-Registration".
if $WANT_TUWUNEL && $WANT_GO && [ -f "$REPO_ROOT/scripts/register-appservice.sh" ]; then
  # Schnelltest: kann appservice als @agent-test im namespace operieren?
  AS_TOKEN=$(grep '^MATRIX_AS_TOKEN=' "$REPO_ROOT/go-appservice/.env.development" 2>/dev/null | cut -d= -f2-)
  if [ -n "$AS_TOKEN" ]; then
    NS_CHECK=$(curl -s -o /dev/null -w "%{http_code}" -m 3 \
      -X PUT -H "Authorization: Bearer ${AS_TOKEN}" -H 'Content-Type: application/json' \
      -d '{"displayname":"probe"}' \
      "http://localhost:$PORT_TUWUNEL/_matrix/client/v3/profile/@agent-probe:matrix.local/displayname?user_id=@agent-probe:matrix.local" 2>/dev/null)
    if [ "$NS_CHECK" = "200" ]; then
      log "appservice namespace OK (already registered)"
    elif [ "$NS_CHECK" = "403" ] || [ "$NS_CHECK" = "400" ]; then
      # 400 = M_EXCLUSIVE (namespace unbekannt), 403 = auth-issue. Register nötig.
      # Alice muss existieren (als first-user-admin für !admin-command).
      if curl -s -m 2 -X POST "http://localhost:$PORT_TUWUNEL/_matrix/client/v3/login" \
           -H 'Content-Type: application/json' \
           -d '{"type":"m.login.password","identifier":{"type":"m.id.user","user":"alice"},"password":"alice-dev-password-2026"}' \
           2>/dev/null | grep -q access_token; then
        log "appservice namespace fehlt → registriere via admin-command…"
        "$REPO_ROOT/scripts/register-appservice.sh" 2>&1 | sed 's/^/  /' || \
          warn "register failed — agent-mention wird nicht funktionieren"
      else
        warn "alice fehlt → skip register. Erst: ./scripts/setup-users.sh"
      fi
    fi
  fi
fi

# ─── Go Appservice (local process) ───────────────────────────────────────────
if $WANT_GO; then
  if [ -f "$REPO_ROOT/go-appservice/.env.development" ]; then
    spawn "go-appservice" "$REPO_ROOT/go-appservice" \
      env GO_ENV=development bash -c 'go run -tags goolm ./cmd/appservice'
  else
    warn "go-appservice/.env.development fehlt — skip"
  fi
fi

# ─── Python services via uv run (APP_ENV=development lädt .env.development) ──
UV_APP_ENV="APP_ENV=development"

if $WANT_AGENT; then
  if $USE_MOCK_AGENT; then
    spawn "python-agent" "$REPO_ROOT/python-backend" \
      env $UV_APP_ENV uv run python -m mock.mock_agent
  else
    spawn "python-agent" "$REPO_ROOT/python-backend" \
      env $UV_APP_ENV uv run python -m uvicorn agent.app:app --host 127.0.0.1 --port "$PORT_AGENT" --reload
  fi
fi

if $WANT_BRIDGE; then
  spawn "python-bridge" "$REPO_ROOT/python-backend" \
    env $UV_APP_ENV uv run python -m uvicorn bridge.app:app --host 127.0.0.1 --port "$PORT_BRIDGE" --reload
fi

if $WANT_INGESTION; then
  spawn "python-ingestion" "$REPO_ROOT/python-backend" \
    env $UV_APP_ENV uv run python -m ingestion.worker
fi

# ─── Frontend ────────────────────────────────────────────────────────────────
if $WANT_FRONTEND; then
  spawn "frontend-merger" "$REPO_ROOT/frontend_merger" bun run dev
fi

# ─── Ready Report ────────────────────────────────────────────────────────────
sleep 2
log ""
log "─── Stack Status ─────────────────────────────────────────────────"
declare -A LBL=(
  [$PORT_TUWUNEL]="tuwunel         (Matrix homeserver)"
  [$PORT_NATS]="nats            (message bus)"
  [$PORT_POSTGRES]="postgres        (state)"
  [$PORT_GARAGE_S3]="garage          (S3 storage)"
  [$PORT_SEAWEED_S3]="seaweedfs       (S3 storage)"
  [$PORT_LITELLM]="litellm         (LLM gateway)"
  [$PORT_LLM_MOCK]="llm-mock        (mock LLM)"
  [$PORT_SANDBOX]="opensandbox     (exec-12)"
  [$PORT_LIVEKIT]="livekit         (MatrixRTC)"
  [$PORT_LK_JWT]="lk-jwt          (LiveKit JWT)"
  [$PORT_COTURN]="coturn          (TURN relay)"
  [$PORT_OPENOBSERVE]="openobserve     (observability)"
  [$PORT_VALKEY]="valkey          (cache)"
  [$PORT_PGBOUNCER]="pgbouncer       (db pool)"
  [$PORT_FALKORDB]="falkordb        (KG)"
  [$PORT_NORNIC]="nornic          (KG)"
  [$PORT_GO]="go-appservice   (local)"
  [$PORT_AGENT]="python-agent    (local)"
  [$PORT_BRIDGE]="python-bridge   (local)"
  [$PORT_INGESTION]="python-ingest   (local)"
  [$PORT_MERGER]="frontend-merger (local)"
)
for p in $PORT_TUWUNEL $PORT_NATS $PORT_POSTGRES $PORT_GARAGE_S3 $PORT_SEAWEED_S3 \
         $PORT_LITELLM $PORT_LLM_MOCK $PORT_SANDBOX $PORT_LIVEKIT $PORT_LK_JWT \
         $PORT_COTURN $PORT_OPENOBSERVE $PORT_VALKEY $PORT_PGBOUNCER \
         $PORT_FALKORDB $PORT_NORNIC $PORT_GO $PORT_AGENT $PORT_BRIDGE \
         $PORT_INGESTION $PORT_MERGER; do
  if port_up "$p"; then
    printf "  \033[32m✓\033[0m :%-5s  %s\n" "$p" "${LBL[$p]}"
  fi
done
log ""
log "Tail:       tail -F $LOG_DIR/*.log"
log "Status:     $0 --status"
log "Kill all:   $0 --kill"
log "Kill one:   $0 --kill=<service>"
log "Add more:   $0 --<flag>  (additive, laufende services bleiben)"
