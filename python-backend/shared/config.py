from __future__ import annotations

import os

# Single source of truth for internal service URLs.
# All python-* packages must import from here instead of reading env vars directly.

GO_GATEWAY_URL: str = os.environ.get(
    "GO_GATEWAY_BASE_URL", "http://127.0.0.1:8090"
).strip()
