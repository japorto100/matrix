#!/usr/bin/env bash
# backup-postgres.sh — einfacher pg_dump Backup für Dev/minimale Prod
#
# Erstellt gzip-komprimierten SQL-Dump der matrix-DB.
# Keine PITR (Point-in-Time-Recovery) — für Prod später pgBackRest evaluieren.
#
# Usage:
#   ./scripts/backup-postgres.sh                    # dump → /mnt/cold-storage/backup/postgres/
#   ./scripts/backup-postgres.sh /custom/path       # dump → custom location
#   ./scripts/backup-postgres.sh --keep 14          # retention: 14 Tage (default: 7)
#
# Cron-entry (daily 3am):
#   0 3 * * *  /home/lipfi2/code/matrix/scripts/backup-postgres.sh >> /tmp/pg-backup.log 2>&1
#
# Voraussetzung: matrix-postgres-container läuft.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${1:-/mnt/cold-storage/backup/postgres}"
KEEP_DAYS=7

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep) KEEP_DAYS="$2"; shift 2 ;;
        --help|-h) sed -n '2,15p' "$0"; exit 0 ;;
        *) if [[ "$1" != --* ]]; then BACKUP_DIR="$1"; fi; shift ;;
    esac
done

# Load POSTGRES_USER/DB from root .env
if [[ -f "$REPO/.env" ]]; then
    POSTGRES_USER=$(grep '^POSTGRES_USER=' "$REPO/.env" | cut -d= -f2-)
    POSTGRES_DB=$(grep '^POSTGRES_DB=' "$REPO/.env" | cut -d= -f2-)
fi
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-hindsight_dev}
POSTGRES_CONTAINER=${POSTGRES_CONTAINER:-matrix-postgres}

mkdir -p "$BACKUP_DIR"
TS=$(date +%Y-%m-%d_%H-%M-%S)
OUTFILE="$BACKUP_DIR/matrix-${POSTGRES_DB}-${TS}.sql.gz"

echo "═══ Postgres Backup ═══"
echo "  DB:       $POSTGRES_DB"
echo "  User:     $POSTGRES_USER"
echo "  Target:   $OUTFILE"
echo "  Retention: $KEEP_DAYS days"
echo ""

# Check container is running
if ! podman ps --format "{{.Names}}" | grep -q "^${POSTGRES_CONTAINER}$"; then
    echo "ERROR: $POSTGRES_CONTAINER container is not running" >&2
    echo "       Run: ./scripts/dev-stack.sh --postgres" >&2
    exit 1
fi

# Dump (all schemas: public, storage, matrix_crypto, agent, ingestion)
echo "[$(date +%H:%M:%S)] Starting pg_dump..."
podman exec "$POSTGRES_CONTAINER" pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --verbose 2>&1 \
    | gzip -c > "$OUTFILE"

SIZE=$(du -h "$OUTFILE" | cut -f1)
echo "[$(date +%H:%M:%S)] [OK] Backup: $OUTFILE ($SIZE)"

# Cleanup old backups
echo ""
echo "═══ Cleanup (older than $KEEP_DAYS days) ═══"
find "$BACKUP_DIR" -name "matrix-*.sql.gz" -mtime +$KEEP_DAYS -print -delete 2>/dev/null | head
echo ""

# Verify latest backup integrity
echo "═══ Integrity check ═══"
if gzip -t "$OUTFILE" 2>/dev/null; then
    echo "  [OK] gzip-integrity validated"
else
    echo "  [FAIL] gzip-integrity check failed!" >&2
    exit 1
fi

# Check backup is non-trivial (>10KB for even empty DB structure)
if [[ $(stat -c%s "$OUTFILE") -lt 10240 ]]; then
    echo "  [WARN] Backup suspiciously small ($SIZE) — check if DB is populated" >&2
fi

echo ""
echo "═══ Done ═══"
echo "  Restore: gunzip -c $OUTFILE | podman exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB"
