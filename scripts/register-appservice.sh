#!/usr/bin/env bash
# register-appservice.sh — registriert homeserver/registration.yaml bei tuwunel
# via admin-command. Idempotent: bei "Duplicate id" wird erst unregistered.
#
# Tuwunel v1.6.0 stable hat bugs mit auto-load (inline-config + appservice_dir),
# daher dynamic via #admins room. Alice muss als first-user-admin registriert
# sein (setup-users.sh).

set -u
set -o pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HS="${MATRIX_HOMESERVER_URL:-http://localhost:8448}"
YAML="$REPO/homeserver/appservices/registration.yaml"
[ ! -f "$YAML" ] && YAML="$REPO/homeserver/registration.yaml"
ADMIN_USER="${MATRIX_ADMIN_USER:-alice}"
ADMIN_PASSWORD="${MATRIX_ADMIN_PASSWORD:-alice-dev-password-2026}"
ADMIN_TOKEN="${MATRIX_ADMIN_ACCESS_TOKEN:-${MATRIX_ACCESS_TOKEN:-}}"

log()  { printf "\033[36m[register-as]\033[0m %s\n" "$*"; }
ok()   { printf "\033[32m[register-as]\033[0m %s\n" "$*"; }
warn() { printf "\033[33m[register-as]\033[0m %s\n" "$*"; }
die()  { printf "\033[31m[register-as] ERROR: %s\033[0m\n" "$*" >&2; exit 1; }

[ ! -f "$YAML" ] && die "registration.yaml nicht gefunden in homeserver/"

load_env_token() {
  local env_file="$REPO/frontend_merger/.env.local"
  [ -n "$ADMIN_TOKEN" ] && return 0
  [ ! -f "$env_file" ] && return 0
  ADMIN_TOKEN=$(grep -E '^MATRIX_ACCESS_TOKEN=' "$env_file" | tail -1 | cut -d= -f2-)
}

login_admin() {
  curl -sSf -X POST "$HS/_matrix/client/v3/login" \
    -H 'Content-Type: application/json' \
    -d "$(python3 - "$ADMIN_USER" "$ADMIN_PASSWORD" <<'PY'
import json
import sys

print(json.dumps({
    "type": "m.login.password",
    "identifier": {"type": "m.id.user", "user": sys.argv[1]},
    "password": sys.argv[2],
}))
PY
)" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null
}

validate_token() {
  curl -sSf -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "$HS/_matrix/client/v3/account/whoami" >/dev/null
}

# Admin user muss existieren und im Tuwunel-Admin-Room sein.
load_env_token
if [ -n "$ADMIN_TOKEN" ] && validate_token; then
  log "$ADMIN_USER token accepted"
else
  ADMIN_TOKEN=$(login_admin) || \
    die "$ADMIN_USER login failed. Set MATRIX_ADMIN_ACCESS_TOKEN or refresh frontend_merger/.env.local via setup-users.sh."
  log "$ADMIN_USER logged in"
fi

# Admin-room finden
ADMIN_ROOM=$(curl -sSf -H "Authorization: Bearer ${ADMIN_TOKEN}" "$HS/_matrix/client/v3/joined_rooms" \
  | python3 -c "import sys,json; [print(r) for r in json.load(sys.stdin).get('joined_rooms',[])]" \
  | head -1)

[ -z "$ADMIN_ROOM" ] && die "$ADMIN_USER is in no admin room (is this the first-user-admin?)"
log "admin room: $ADMIN_ROOM"

send_admin() {
  local body=$1
  local txn="t$(date +%s%N)"
  local body_json
  body_json=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$body")
  curl -sSf -X PUT -H "Authorization: Bearer ${ADMIN_TOKEN}" -H 'Content-Type: application/json' \
    -d "{\"msgtype\":\"m.text\",\"body\":${body_json}}" \
    "$HS/_matrix/client/v3/rooms/${ADMIN_ROOM}/send/m.room.message/${txn}" >/dev/null || \
    warn "send failed"
}

wait_reply() {
  local match=$1
  local timeout=${2:-5}
  local i=0
  while [ $i -lt $timeout ]; do
    sleep 1
    local latest
    latest=$(curl -sSf -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      "$HS/_matrix/client/v3/rooms/${ADMIN_ROOM}/messages?limit=3&dir=b" \
      | python3 -c "import sys,json; [print(e.get('content',{}).get('body','')) for e in json.load(sys.stdin).get('chunk',[]) if e.get('sender','').startswith('@conduit')]" 2>/dev/null \
      | head -5)
    if echo "$latest" | grep -qE "$match"; then
      echo "$latest"
      return 0
    fi
    i=$((i+1))
  done
  return 1
}

# Parse appservice-id aus yaml
APP_ID=$(grep -E '^id:' "$YAML" | awk '{print $2}')
[ -z "$APP_ID" ] && die "id: nicht gefunden in $YAML"
log "appservice-id: $APP_ID"

# Erst check ob already registered
log "check if already registered…"
send_admin "!admin appservices list"
LIST_REPLY=$(wait_reply "Appservices" 3 || echo "")
if echo "$LIST_REPLY" | grep -qE "$APP_ID\b"; then
  log "'$APP_ID' already registered — unregistering first"
  send_admin "!admin appservices unregister $APP_ID"
  wait_reply "unregistered|removed|not registered|error" 5 >/dev/null || true
  ok "unregister done"
fi

# Register mit yaml-content
YAML_CONTENT=$(cat "$YAML")
log "registering '$APP_ID'…"
send_admin "!admin appservices register
\`\`\`
${YAML_CONTENT}
\`\`\`"
REPLY=$(wait_reply "registered|Duplicate|error|Failed" 5 || echo "no-reply")

if echo "$REPLY" | grep -qiE "registered|success"; then
  ok "appservice '$APP_ID' successfully registered"
elif echo "$REPLY" | grep -qiE "duplicate"; then
  warn "already registered — unregister failed above?"
elif echo "$REPLY" | grep -qiE "failed|error"; then
  die "registration failed: $REPLY"
else
  warn "no clear reply: $REPLY"
fi

echo ""
log "verify with: !admin appservices list"
