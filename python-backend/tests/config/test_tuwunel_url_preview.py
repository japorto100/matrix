from __future__ import annotations

import tomllib
from pathlib import Path


def test_active_tuwunel_config_disables_url_preview_allowlists():
    repo = Path(__file__).resolve().parents[3]
    config = tomllib.loads((repo / "homeserver/tuwunel.v1.6.toml").read_text())
    global_cfg = config["global"]

    assert global_cfg["url_preview_domain_contains_allowlist"] == []
    assert global_cfg["url_preview_domain_explicit_allowlist"] == []
    assert global_cfg["url_preview_url_contains_allowlist"] == []
