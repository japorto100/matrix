#!/usr/bin/env bash
set -euo pipefail

# Optional, explicit model download for kg_pipeline/extraction_layout (Phase 2).
# This script is intentionally NOT invoked automatically.

python -m spacy download en_core_web_sm

