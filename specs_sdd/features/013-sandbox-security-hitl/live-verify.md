---
title: Sandbox, Security and HITL Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 013
---

# Live Verify

## Source Checks

- `exec-12` Phase 1/2 implemented items are either verified here or marked
  stale with reason.
- `exec-security` shipped/open split is reflected in tasks.
- ADR-004 surface-dialog decision is represented in gates.
- Superpower implementation log entries for Skills-Guard drawer are checked
  against current code.
- `16-security.md` Matrix SSRF/XSS/E2EE decisions are checked against config.

## Sandbox Runtime

- Start sandbox profile.
- Run safe command/script.
- Confirm output is captured.
- Confirm denied operation is blocked or isolated.
- Upload CSV/JSON/code sample and confirm sandbox result.
- Run browser sandbox smoke test and capture artifact.
- Stop/restart sandbox and confirm graceful error message when unavailable.

## 2026-04-26 OpenSandbox Runtime Smoke

Status: partial pass; code-execution runtime is live, egress/browser/file gates
remain open.

Evidence:

- `./scripts/dev-stack.sh --sandbox` now targets only `opensandbox-server` and
  reports Sandbox on `:8080`; the obsolete second `opensandbox` service on
  `:8100` was not used because it defaults to Kubernetes mode without
  kubeconfig.
- `opensandbox-api-gateway` is healthy on `http://127.0.0.1:8080/health`.
- Fixed Docker healthcheck: the OpenSandbox image lacks `curl`, so compose now
  uses Python `urllib.request`.
- Fixed SDK addressing: Matrix now maps legacy
  `OPENSANDBOX_SERVER_URL`/`OPEN_SANDBOX_URL` to OpenSandbox SDK
  `ConnectionConfig(domain=...)`, and sets `OPEN_SANDBOX_DOMAIN` in generated
  env.
- Fixed local Docker/Podman connectivity: SDK uses `use_server_proxy=true`.
- Fixed local runtime network: `sandbox-config.toml` uses Docker
  `network_mode="bridge"` because OpenSandbox endpoint/proxy resolution fails
  with `network_mode="none"` (`DOCKER::NETWORK_MODE_ENDPOINT_UNAVAILABLE`).
  Denied egress must be verified via OpenSandbox `networkPolicy`/egress sidecar
  in T014.
- Fixed image default: `SANDBOX_CODE_IMAGE` now uses upstream documented
  `sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.2`.
  First pull completed locally; image size is about 9.65 GB.
- Added cold-start budget:
  `OPENSANDBOX_REQUEST_TIMEOUT_SEC=180`,
  `OPENSANDBOX_READY_TIMEOUT_SEC=90`.
- Direct `SandboxManager.execute_code(code="print(2 + 3)")` returned
  `stdout='5\n'`, `stderr=''`, `exit_code=0`, `error=None`.
- Direct `SandboxExecuteTool.execute(code="print(7 * 6)")` returned
  `stdout='42\n'`, `stderr=''`, `exit_code=0`, `error=None`.
- Focused tests: `tests/agent/sandbox/test_config.py` => `6 passed`.
- Ruff: `agent/sandbox/config.py`, `agent/sandbox/manager.py` and
  `tests/agent/sandbox/test_config.py` pass.

Residual risk:

- Browser sandbox still uses `tradeview/sandbox-browser:v1` and remains
  unverified.
- File upload, egress deny/allow behavior and limit/TTL caps still need live
  probes.
- Local cold start is slow after image/server reset because OpenSandbox pulls
  and warms `code-interpreter` and `execd`.

## Prompt / Redaction

- Submit benign scheduled task prompt.
- Submit malicious/prompt-injection scheduled task prompt.
- Confirm scanner blocks high-risk prompt.
- Send sample sensitive data through redaction path.
- Confirm sensitive value is redacted in logs/output.
- Export trajectory/sample span and confirm redacted value does not reappear.
- Confirm non-secret text remains readable enough for debugging.

## HITL / UI

- Import a dangerous synthetic skill.
- Confirm structured 422 body includes verdict and suggested action.
- Confirm BFF opens Skills-Guard drawer/dialog.
- Approve once and confirm import retry succeeds.
- Deny and confirm import remains blocked.
- Confirm consent/audit events record both outcomes.
- Confirm Control UI Security/Sandbox/Permissions state reflects result.

## Matrix Security

- Try URL preview path/config; confirm previews are disabled.
- Send sanitized markdown/XSS sample; confirm unsafe HTML is stripped.
- Confirm private/E2EE and agent-room trust boundary matches feature 006.

## Result

partial pass; OpenSandbox code execution is live. Remaining work is browser,
file upload, egress policy and HITL/consent live verification.

## 2026-04-27 File Upload Path Probe

Status: static pass, live blocked before code execution.

Evidence:

- Code fix: `SandboxManager.execute_file` now exists and wraps the existing
  `execute_code(upload_files=...)` lifecycle. `SandboxResult` also exposes
  `success` and `to_dict()` for `FileAnalyzeTool` audit/output compatibility.
- Static tests:
  `cd python-backend && uv run pytest tests/agent/sandbox/test_config.py tests/agent/sandbox/test_manager_file.py -q`
  => `8 passed`.
- Ruff:
  `cd python-backend && uv run ruff check agent/sandbox/manager.py tests/agent/sandbox/test_manager_file.py`
  => pass.
- Live server health:
  `GET http://127.0.0.1:8080/health` returned `200`.
- Live file probe reached OpenSandbox and attempted to create a
  `code-interpreter:v1.0.2` sandbox, but failed before code execution:
  `Failed to create directory /opt/opensandbox ... broken pipe`.
- Host storage at the time was `/` 93% full with about 7.5 GB free; the active
  code-interpreter image is about 9.65 GB. Treat this as an OpenSandbox/Podman
  runtime/storage blocker, not a successful file-upload gate.

Remaining:

- Re-run live `execute_file` after fixing OpenSandbox rootless Podman/archive
  behavior and/or freeing SSD/container storage.
- Only then mark T012 file upload and T015 resource/TTL/output caps live.
