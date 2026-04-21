#!/usr/bin/env bash
# setup-garage.sh — Garage S3 Initial Setup (idempotent)
#
# 1. Startet garage-container (via compose)
# 2. Initialisiert single-node cluster (layout assign + apply)
# 3. Erstellt S3-key `matrix-key`
# 4. Erstellt bucket `matrix-media`, grants read+write
# 5. Schreibt Keys in homeserver/tuwunel.image.toml (ersetzt platzhalter)
# 6. Schreibt Keys auch in go-appservice/.env.development (ARTIFACT_STORAGE_*)
#
# Re-run safe: erkennt bereits angelegte keys/buckets und macht KEINE duplicates.

set -u
set -o pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
GARAGE_CONTAINER="garage"
S3_ENDPOINT="http://127.0.0.1:3900"
BUCKETS=("matrix-media" "matrix-artifacts")   # tuwunel + go-appservice
KEY_NAME="matrix-key"
TUWUNEL_CFG="$REPO/homeserver/tuwunel.v1.6.toml"
GO_ENV="$REPO/go-appservice/.env.development"

log()  { printf "\033[36m[garage-setup]\033[0m %s\n" "$*"; }
ok()   { printf "\033[32m[garage-setup]\033[0m %s\n" "$*"; }
warn() { printf "\033[33m[garage-setup]\033[0m %s\n" "$*"; }
die()  { printf "\033[31m[garage-setup] ERROR: %s\033[0m\n" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

# Container-runtime detect (podman oder docker)
if have podman; then CRI=podman
elif have docker; then CRI=docker
else die "weder podman noch docker gefunden"
fi

# Choose compose variant
if have podman-compose; then COMPOSE="podman-compose"
elif have docker-compose;  then COMPOSE="docker-compose"
else die "weder podman-compose noch docker-compose gefunden"
fi

# ─── 1. Start garage container ────────────────────────────────────────────────
# podman-compose <1.1 hat kein --profile flag → nutzen COMPOSE_PROFILES env-var.
# docker-compose + newer podman-compose respektieren die env-var auch.
log "starting garage container…"
(cd "$REPO" && COMPOSE_PROFILES=storage-garage $COMPOSE up -d garage 2>&1) | sed 's/^/  /' \
  || die "compose up failed"

# Wait for garage S3 API
i=0; while [ $i -lt 30 ]; do
  if $CRI exec "$GARAGE_CONTAINER" /garage status >/dev/null 2>&1; then
    ok "garage responds"
    break
  fi
  sleep 1; i=$((i+1))
done
[ $i -ge 30 ] && die "garage didn't start in 30s"

# ─── 2. Cluster-Layout initialisieren (idempotent) ──────────────────────────
# Frischer cluster: layout version = 0, nodes haben "NO ROLE ASSIGNED".
# Initialisiert: layout version >= 1, nodes haben zone+capacity+tag zugewiesen.
LAYOUT_OUT=$($CRI exec "$GARAGE_CONTAINER" /garage layout show 2>&1)
if echo "$LAYOUT_OUT" | grep -qE "layout version: 0|No nodes currently have a role"; then
  log "initializing single-node cluster layout…"
  # garage node id: gibt "<node-id>@<addr>\n\nTo instruct..." aus. Erste Zeile nehmen.
  NODE_ID=$($CRI exec "$GARAGE_CONTAINER" /garage node id 2>/dev/null | head -1 | cut -d'@' -f1)
  [ -z "$NODE_ID" ] && die "could not parse garage node id"
  log "node-id: ${NODE_ID:0:16}…"

  # node-id ZUERST (positional), dann flags. `-t <tags>...` ist multi-value und
  # würde sonst den node-id als weiteren tag schlucken.
  $CRI exec "$GARAGE_CONTAINER" /garage layout assign "$NODE_ID" -z dc1 -c 1G -t node1 \
    || die "layout assign failed"
  $CRI exec "$GARAGE_CONTAINER" /garage layout apply --version 1 \
    || die "layout apply failed"
  ok "cluster layout applied"
else
  ok "cluster layout already initialized"
fi

# ─── 3. S3-Key erstellen (idempotent) ─────────────────────────────────────────
if $CRI exec "$GARAGE_CONTAINER" /garage key list 2>/dev/null | grep -q "$KEY_NAME"; then
  log "key '$KEY_NAME' exists — re-fetching info…"
  KEY_INFO=$($CRI exec "$GARAGE_CONTAINER" /garage key info --show-secret "$KEY_NAME" 2>/dev/null)
else
  log "creating key '$KEY_NAME'…"
  KEY_INFO=$($CRI exec "$GARAGE_CONTAINER" /garage key create "$KEY_NAME" 2>&1)
  ok "key created"
fi

# Parse access-key-id + secret from output
ACCESS_KEY_ID=$(echo "$KEY_INFO" | grep -E "^Key ID:" | awk '{print $3}')
SECRET_KEY=$(echo "$KEY_INFO" | grep -E "^Secret key:" | awk '{print $3}')

if [ -z "$ACCESS_KEY_ID" ] || [ -z "$SECRET_KEY" ]; then
  warn "failed to parse key info, raw output:"
  echo "$KEY_INFO"
  die "cannot extract access-key / secret"
fi
log "access-key: ${ACCESS_KEY_ID:0:8}… (masked)"

# ─── 4. Buckets erstellen + Permissions (idempotent) ────────────────────────
# Zwei buckets: matrix-media (tuwunel) + matrix-artifacts (go-appservice).
for bucket in "${BUCKETS[@]}"; do
  if $CRI exec "$GARAGE_CONTAINER" /garage bucket list 2>/dev/null | grep -qE "\b$bucket\b"; then
    ok "bucket '$bucket' already exists"
  else
    log "creating bucket '$bucket'…"
    $CRI exec "$GARAGE_CONTAINER" /garage bucket create "$bucket" || die "bucket create '$bucket' failed"
  fi

  log "granting read+write to key '$KEY_NAME' on bucket '$bucket'…"
  $CRI exec "$GARAGE_CONTAINER" /garage bucket allow \
    --key "$KEY_NAME" --read --write "$bucket" 2>/dev/null || warn "bucket allow '$bucket' no-op (already granted)"
done

# ─── 5. tuwunel.image.toml mit Keys aktualisieren ───────────────────────────
if [ -f "$TUWUNEL_CFG" ]; then
  # Replace placeholders (GARAGE_ACCESS_KEY / GARAGE_SECRET_KEY) or existing values
  # Pattern: `key = "..."` and `secret = "..."` in garage.S3 block
  sed -i -E "s|^(\s*key\s*=\s*\")[^\"]*(\"\s*#\s*garage-managed.*)$|\1${ACCESS_KEY_ID}\2|" "$TUWUNEL_CFG"
  sed -i -E "s|^(\s*secret\s*=\s*\")[^\"]*(\"\s*#\s*garage-managed.*)$|\1${SECRET_KEY}\2|" "$TUWUNEL_CFG"
  ok "tuwunel.v1.6.toml keys updated"
else
  warn "$TUWUNEL_CFG nicht gefunden — keys nicht injiziert. Anlegen + garage-managed marker verwenden."
fi

# ─── 6. go-appservice .env.development aktualisieren ─────────────────────────
if [ -f "$GO_ENV" ]; then
  # Provider von seaweedfs → garage switchen (idempotent)
  if grep -qE "^ARTIFACT_STORAGE_PROVIDER=" "$GO_ENV"; then
    sed -i -E "s|^ARTIFACT_STORAGE_PROVIDER=.*|ARTIFACT_STORAGE_PROVIDER=garage|" "$GO_ENV"
  else
    echo "ARTIFACT_STORAGE_PROVIDER=garage" >> "$GO_ENV"
  fi
  # Endpoint auf garage-port 3900
  sed -i -E "s|^ARTIFACT_STORAGE_S3_ENDPOINT=.*|ARTIFACT_STORAGE_S3_ENDPOINT=${S3_ENDPOINT}|" "$GO_ENV"
  sed -i -E "s|^ARTIFACT_STORAGE_S3_ACCESS_KEY_ID=.*|ARTIFACT_STORAGE_S3_ACCESS_KEY_ID=${ACCESS_KEY_ID}|" "$GO_ENV"
  sed -i -E "s|^ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY=.*|ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY=${SECRET_KEY}|" "$GO_ENV"
  sed -i -E "s|^ARTIFACT_STORAGE_S3_REGION=.*|ARTIFACT_STORAGE_S3_REGION=garage|" "$GO_ENV"
  ok "go-appservice/.env.development: ARTIFACT_STORAGE_* → garage"
fi

echo ""
ok "garage setup complete"
echo "    endpoint:       $S3_ENDPOINT"
echo "    buckets:        ${BUCKETS[*]}"
echo "    access-key-id:  $ACCESS_KEY_ID"
echo "    secret-key:     ${SECRET_KEY:0:8}… (masked)"
echo ""
echo "Next: start tuwunel  →  ./scripts/dev-stack.sh --tuwunel16"
