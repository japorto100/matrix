#!/usr/bin/env bash
# sync-storage-creds.sh — Propagiert SEAWEEDFS/GARAGE S3-Keys aus .env in config-files
#
# Root .env ist single-source-of-truth. Bei Key-Rotation: edit .env, run this script.
# Affected files:
#   - tools/seaweedfs/s3.json
#   - homeserver/tuwunel.v1.6.toml
#   - go-appservice/.env.development + .env.production
#
# Usage:
#   ./scripts/sync-storage-creds.sh           # sync from .env
#   ./scripts/sync-storage-creds.sh --dry-run # show what would change

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO/.env"
DRY=false

for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY=true ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found — run scripts/bootstrap-env.py first" >&2
    exit 1
fi

# Extract keys from .env
SW_AK=$(grep '^SEAWEEDFS_S3_ACCESS_KEY=' "$ENV_FILE" | cut -d= -f2-)
SW_SK=$(grep '^SEAWEEDFS_S3_SECRET_KEY=' "$ENV_FILE" | cut -d= -f2-)
GA_AK=$(grep '^GARAGE_S3_ACCESS_KEY='    "$ENV_FILE" | cut -d= -f2-)
GA_SK=$(grep '^GARAGE_S3_SECRET_KEY='    "$ENV_FILE" | cut -d= -f2-)

if [[ -z "$SW_AK" || -z "$SW_SK" ]]; then
    echo "ERROR: SEAWEEDFS_S3_ACCESS_KEY/SECRET_KEY not found in $ENV_FILE" >&2
    exit 1
fi

echo "From $ENV_FILE:"
echo "  SEAWEEDFS_S3_ACCESS_KEY=${SW_AK:0:8}…${SW_AK: -4}"
echo "  SEAWEEDFS_S3_SECRET_KEY=${SW_SK:0:8}…${SW_SK: -4}"
echo "  GARAGE_S3_ACCESS_KEY   =${GA_AK:0:8}…${GA_AK: -4}"
echo ""

run_sed() {
    local file="$1" pattern="$2"
    if [[ "$DRY" == true ]]; then
        echo "[DRY] would patch $file: $pattern"
    else
        sed -i -E "$pattern" "$file"
        echo "[OK] $file"
    fi
}

echo "═══ Syncing storage credentials ═══"

# 1. tools/seaweedfs/s3.json
run_sed "$REPO/tools/seaweedfs/s3.json" \
    "s|\"accessKey\": *\"[^\"]*\"|\"accessKey\": \"$SW_AK\"|"
run_sed "$REPO/tools/seaweedfs/s3.json" \
    "s|\"secretKey\": *\"[^\"]*\"|\"secretKey\": \"$SW_SK\"|"

# 2. homeserver/tuwunel.v1.6.toml — seaweedfs block (active)
TOML="$REPO/homeserver/tuwunel.v1.6.toml"
if [[ "$DRY" == true ]]; then
    echo "[DRY] would patch $TOML: seaweedfs + garage keys"
else
    # Active seaweedfs block
    awk -v ak="$SW_AK" -v sk="$SW_SK" -v ga_ak="$GA_AK" -v ga_sk="$GA_SK" '
        /^\[global\.storage_provider\.seaweedfs\.S3\]/  { in_sw=1; in_ga=0 }
        /^# \[global\.storage_provider\.garage\.S3\]/    { in_sw=0; in_ga=1 }
        /^\[/ && !/seaweedfs|garage/                     { in_sw=0; in_ga=0 }
        in_sw && /^key +=/                               { print "key                    = \"" ak "\""; next }
        in_sw && /^secret +=/                            { print "secret                 = \"" sk "\""; next }
        in_ga && /^# key +=/                             { print "# key                    = \"" ga_ak "\""; next }
        in_ga && /^# secret +=/                          { print "# secret                 = \"" ga_sk "\""; next }
        { print }
    ' "$TOML" > "$TOML.tmp" && mv "$TOML.tmp" "$TOML"
    echo "[OK] $TOML"
fi

# 3. go-appservice/.env.development + .env.production
for f in "$REPO/go-appservice/.env.development" "$REPO/go-appservice/.env.production"; do
    run_sed "$f" "s|^ARTIFACT_STORAGE_S3_ACCESS_KEY_ID=.*|ARTIFACT_STORAGE_S3_ACCESS_KEY_ID=$SW_AK|"
    run_sed "$f" "s|^ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY=.*|ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY=$SW_SK|"
done

echo ""
echo "[OK] All storage credentials synced from $ENV_FILE"
echo ""
echo "Next: restart affected services"
echo "  podman-compose restart seaweedfs tuwunel"
echo "  # Plus go-appservice neu starten via dev-stack.sh"
