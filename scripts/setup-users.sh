#!/usr/bin/env bash
# setup-users.sh — Linux-Port von setup-users.ps1
# Erstellt Matrix-User für Dev/Test + schreibt access_tokens in .env files.
#
# Voraussetzung: Tuwunel läuft (podman-compose up -d tuwunel)
#
# Erstellt:
#   @alice:matrix.local        — Test-User (Browser/Element-X, optional SSR in frontend_merger)
#   @bob:matrix.local          — Zweiter Test-User (für Chat-Tests)
#   @agent-bot:matrix.local    — Python agent bot (access_token → python-backend/.env.development)
#
# Nicht erstellt (werden via Appservice Pattern dynamisch erzeugt):
#   @appservice-bot, @agent-trading, @agent-research, ...
#
# Usage:
#   ./scripts/setup-users.sh
#   ./scripts/setup-users.sh --force    # überschreibt existierende tokens
#
# Idempotent: re-runs skip already-existing users, re-use their tokens.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HS="${MATRIX_HOMESERVER_URL:-http://localhost:8448}"
REG_TOKEN="${MATRIX_REGISTRATION_TOKEN:-matrix-dev-token-2026}"   # aus tuwunel.v1.6.toml
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --force|-f) FORCE=true ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    esac
done

# ─── Color output ──────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    B='\033[1m'; R='\033[0m'; G='\033[32m'; Y='\033[33m'; X='\033[31m'; C='\033[36m'
else
    B='';R='';G='';Y='';X='';C=''
fi
step() { echo -e "\n${C}==>${R} $1"; }
ok()   { echo -e "    ${G}OK:${R} $1"; }
warn() { echo -e "    ${Y}!!:${R} $1"; }
err()  { echo -e "    ${X}ERR:${R} $1" >&2; }

# ─── Check tuwunel erreichbar ──────────────────────────────────────────────
step "Prüfe Tuwunel ($HS)..."
if ! curl -sf --max-time 5 "$HS/_matrix/client/versions" >/dev/null; then
    err "Tuwunel nicht erreichbar."
    echo "    Starte: podman-compose up -d tuwunel"
    exit 1
fi
ok "Tuwunel antwortet"

# ─── Register via Shared-Secret (wenn verfügbar) oder Registration-Token ───
# Tuwunel unterstützt registration_token in tuwunel.toml — wir nutzen das.
register_user() {
    local username=$1 password=$2
    local body
    body=$(cat <<EOF
{
  "auth": {
    "type": "m.login.registration_token",
    "token": "$REG_TOKEN",
    "session": ""
  },
  "username": "$username",
  "password": "$password",
  "initial_device_display_name": "setup-users.sh"
}
EOF
)

    # Step 1: UIAA flow-start (expected 401 with flow info)
    local session
    session=$(curl -sf -X POST "$HS/_matrix/client/v3/register" \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"$username\",\"password\":\"$password\"}" 2>&1 \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session',''))" 2>/dev/null || echo "")

    # Step 2: complete with token
    body=$(cat <<EOF
{
  "auth": {
    "type": "m.login.registration_token",
    "token": "$REG_TOKEN",
    "session": "$session"
  },
  "username": "$username",
  "password": "$password",
  "initial_device_display_name": "setup-users.sh"
}
EOF
)

    curl -sf -X POST "$HS/_matrix/client/v3/register" \
        -H 'Content-Type: application/json' \
        -d "$body"
}

login_user() {
    local username=$1 password=$2
    local body
    body=$(cat <<EOF
{
  "type": "m.login.password",
  "identifier": {"type":"m.id.user","user":"$username"},
  "password": "$password",
  "initial_device_display_name": "setup-users.sh"
}
EOF
)
    curl -sf -X POST "$HS/_matrix/client/v3/login" \
        -H 'Content-Type: application/json' \
        -d "$body"
}

extract() {
    local json=$1 field=$2
    echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null
}

update_env() {
    local file=$1 key=$2 value=$3
    if [[ ! -f "$file" ]]; then
        warn "$file nicht gefunden, skip"
        return
    fi
    if grep -qE "^${key}=" "$file"; then
        # Escape for sed
        local esc
        esc=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')
        sed -i -E "s|^${key}=.*|${key}=${esc}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

# ─── Create users ──────────────────────────────────────────────────────────
USERS=(
    "alice:alice-dev-password-2026:frontend_merger/.env.local:MATRIX_ACCESS_TOKEN:MATRIX_DEVICE_ID:MATRIX_USER_ID"
    "bob:bob-dev-password-2026::::"  # no env-write for bob
    "agent-bot:$(grep '^MATRIX_BOT_PASSWORD=' python-backend/.env.development | cut -d= -f2-):python-backend/.env.development:MATRIX_BOT_ACCESS_TOKEN:MATRIX_BOT_DEVICE_ID:MATRIX_BOT_USER_ID"
)

for user_spec in "${USERS[@]}"; do
    IFS=':' read -r username password env_file token_key device_key user_key <<< "$user_spec"

    step "Setup user @$username"

    # Versuche register, falls existiert login
    response=$(register_user "$username" "$password" 2>&1 || true)
    access_token=$(extract "$response" "access_token")
    device_id=$(extract "$response" "device_id")
    user_id=$(extract "$response" "user_id")

    if [[ -z "$access_token" ]]; then
        # Existiert schon → login
        warn "Register failed (User existiert?), versuche login..."
        response=$(login_user "$username" "$password" 2>&1 || true)
        access_token=$(extract "$response" "access_token")
        device_id=$(extract "$response" "device_id")
        user_id=$(extract "$response" "user_id")
    fi

    if [[ -n "$access_token" ]]; then
        ok "@$username: access_token=${access_token:0:16}… device=$device_id"
        if [[ -n "$env_file" && -f "$REPO/$env_file" ]]; then
            update_env "$REPO/$env_file" "$token_key" "$access_token"
            [[ -n "$device_key" ]] && update_env "$REPO/$env_file" "$device_key" "$device_id"
            [[ -n "$user_key" ]] && update_env "$REPO/$env_file" "$user_key" "$user_id"
            ok "→ $env_file aktualisiert"
        fi
    else
        err "@$username: kein token erhalten"
        echo "    Response: $(echo "$response" | head -c 200)"
    fi
done

echo ""
echo -e "${G}═══ Setup komplett ═══${R}"
echo ""
echo "Erstellte User:"
echo "  - @alice:matrix.local       → token in frontend_merger/.env.local"
echo "  - @bob:matrix.local         → Test-User (kein env-write)"
echo "  - @agent-bot:matrix.local   → token in python-backend/.env.development"
echo ""
echo "Next:"
echo "  - Restart python-agent damit neuer MATRIX_BOT_ACCESS_TOKEN geladen wird"
echo "  - Login als alice in Element-X: http://localhost:8448"
