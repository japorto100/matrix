#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEAWEED_DIR="${ROOT_DIR}/tools/seaweedfs"
SEAWEED_DATA_DIR="${SEAWEED_DIR}/data"
SEAWEED_BIN="${SEAWEED_BIN:-${SEAWEED_DIR}/weed}"

if [[ -x "${SEAWEED_BIN}" ]]; then
  BIN="${SEAWEED_BIN}"
elif command -v weed >/dev/null 2>&1; then
  BIN="$(command -v weed)"
else
  echo "SeaweedFS binary not found. Put 'weed' on PATH or at ${SEAWEED_BIN}." >&2
  exit 1
fi

mkdir -p "${SEAWEED_DATA_DIR}"

exec "${BIN}" server \
  -dir="${SEAWEED_DATA_DIR}" \
  -s3 \
  -s3.config="${SEAWEED_DIR}/s3.json" \
  -ip=127.0.0.1 \
  -master.port=9333 \
  -volume.port=18080 \
  -filer.port=8888 \
  -s3.port=8333
