from __future__ import annotations

from agent.sandbox.config import (
    get_code_image,
    get_sandbox_connection_config,
    get_sandbox_ready_timeout,
    get_sandbox_server_url,
)


def test_sandbox_server_url_prefers_matrix_env(monkeypatch):
    monkeypatch.delenv("OPEN_SANDBOX_DOMAIN", raising=False)
    monkeypatch.setenv("OPENSANDBOX_SERVER_URL", "http://localhost:8080")
    monkeypatch.setenv("OPEN_SANDBOX_URL", "http://localhost:8100")

    assert get_sandbox_server_url() == "http://localhost:8080"


def test_sandbox_connection_config_bridges_legacy_env_names(monkeypatch):
    monkeypatch.delenv("OPEN_SANDBOX_DOMAIN", raising=False)
    monkeypatch.delenv("OPENSANDBOX_REQUEST_TIMEOUT_SEC", raising=False)
    monkeypatch.setenv("OPENSANDBOX_SERVER_URL", "http://localhost:8080")
    monkeypatch.setenv("OPEN_SANDBOX_URL", "http://localhost:8100")

    config = get_sandbox_connection_config()

    assert config.domain == "http://localhost:8080"
    assert config.get_base_url() == "http://localhost:8080/v1"
    assert config.request_timeout.total_seconds() == 180
    assert config.use_server_proxy is True


def test_sandbox_connection_config_prefers_sdk_env_name(monkeypatch):
    monkeypatch.setenv("OPEN_SANDBOX_DOMAIN", "http://sandbox.example:8080")
    monkeypatch.setenv("OPENSANDBOX_SERVER_URL", "http://localhost:8080")

    config = get_sandbox_connection_config()

    assert config.domain == "http://sandbox.example:8080"


def test_code_image_default_matches_opensandbox_registry(monkeypatch):
    monkeypatch.delenv("SANDBOX_CODE_IMAGE", raising=False)

    assert get_code_image() == (
        "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/"
        "code-interpreter:v1.0.2"
    )


def test_sandbox_timeouts_are_configurable(monkeypatch):
    monkeypatch.setenv("OPENSANDBOX_REQUEST_TIMEOUT_SEC", "240")
    monkeypatch.setenv("OPENSANDBOX_READY_TIMEOUT_SEC", "120")

    assert get_sandbox_connection_config().request_timeout.total_seconds() == 240
    assert get_sandbox_ready_timeout().total_seconds() == 120


def test_sandbox_server_proxy_can_be_disabled(monkeypatch):
    monkeypatch.setenv("OPENSANDBOX_USE_SERVER_PROXY", "false")

    assert get_sandbox_connection_config().use_server_proxy is False
