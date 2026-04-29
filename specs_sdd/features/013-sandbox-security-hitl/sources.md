---
title: Sandbox Security HITL Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 013
---

# Sources

## Normative Local Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/exec-12-sandbox-security.md` | Primary implementation history for OpenSandbox Phase 1 and security-hardening Phase 2. |
| `specs/execution/exec-security.md` | Umbrella posture for redaction, Skills-Guard HITL, audit integrity and scheduler prompt-injection defense. |
| `docs/superpowers/findings/2026-04-23-adr-004-sandbox-hitl-layer.md` | Accepted decision: Skills-Guard HITL lives at surface-dialog/consent layer, not sandbox layer. |
| `specs/16-security.md` | Matrix-specific SSRF, E2EE, XSS and SDK-behavior decisions. |
| `specs/execution/superpower-impl-log.md` | Evidence that Skills-Guard structured error and drawer landed after ADR-004. Needs live verify. |
| `specs/execution/archive/opensandbox-gemini-usecases.txt` | Usecase seed for sandboxed code execution and feature-preview workflows. |
| `main_docs/root/AGENT_SECURITY.md` | Retrieval broker, capability envelope, storage write path and evidence-completeness gates. |
| `main_docs/root/AGENT_HARNESS.md` | Harness/sandboxing/complete mediation reference. |

## External Repos / Products

| Source | Use |
|---|---|
| OpenSandbox / `open-sandbox.ai` / `github.com/alibaba/OpenSandbox` | Code-execution runtime boundary, container lifecycle, SDK/API behavior. Adopted as sandbox provider. |
| OpenSandbox Code Interpreter example (`https://open-sandbox.ai/examples/code-interpreter/readme`) | Adopted local code-interpreter image source: `sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.2`. |
| OpenSandbox server/development docs (`https://open-sandbox.ai/server/development`) | Docker egress/networking reference: `networkPolicy` egress sidecar requires Docker `network_mode="bridge"`, so Matrix cannot use Docker `none` while expecting execd/proxy endpoints. |
| OpenSandbox single-host networking docs (`https://open-sandbox.ai/design/single-host-network`) | Explains endpoint/proxy resolution and why local clients may need server-proxy mode or host-reachable endpoint configuration. |
| `opensandbox`, `opensandbox-code-interpreter` PyPI packages | Python SDK and code-interpreter integration; old SDK notes document API mismatches. |
| pentagi patterns | Structured audit, rate limiting, grace termination, installer hardening, template validation inspiration. |
| deer-flow GuardrailProvider pattern | Consent provider abstraction and guardrail framing. |
| Hermes `_ref/hermes-agent/tools/skills_guard.py` | Source pattern for static skills import guard; matrix port keeps surface-level verdict API. |
| Hermes `_ref/hermes-agent/agent/redact.py` | Source pattern for static redaction; matrix expands it for persisted spans and trajectory exports. |
| ProtectAI `deberta-v3-base-prompt-injection-v2` | Optional CPU prompt-injection classifier for high-risk tool outputs. Adopted as P2 when model is present. |

## Security Standards / Incidents

| Source | Use |
|---|---|
| OWASP LLM01:2025 | Compliance framing for prompt injection defenses: privilege minimization, HITL, structural separation, content tagging and filtering. |
| Matrix/Synapse CVE-2023-32683 | Concrete URL preview SSRF precedent; supports decision to keep previews off. |
| Synapse URL preview docs | Server-side preview risk model: arbitrary room members can trigger homeserver fetches. |
| Element Web E2EE preview default | Reference behavior: previews disabled by default in encrypted rooms due to privacy/security risk. |

## Open Research Sources

These are not adopted architecture yet. They are evaluation inputs for a possible
Tier-3 redaction/secret-detection decision.

| Source | Open Question |
|---|---|
| Cloudflare Secret-Detection 2025 paper | Does ML secret scanning reduce false negatives on matrix span samples enough to justify complexity? |
| GitHub Secret Scanning ML work | Is API/service integration useful for enterprise deployments or too externalized? |
| Trufflehog v4 | Can local/library detection improve over regex without large latency or licensing cost? |
| GitGuardian API | Commercial API cost/latency/privacy tradeoff for redaction. |
| OWASP 2026 LLM leak taxonomy | Which leak classes need context-aware or ML detection rather than regex? |

## Adopted Into Matrix

- Sandbox is only for untrusted code execution. Internal deterministic backend
  logic and normal API calls stay outside the sandbox.
- OpenSandbox runs LLM/user code with resource, timeout, filesystem and egress
  constraints.
- Consent system is the canonical approval mechanism; sandbox-specific HITL is
  rejected for current Skills-Guard imports.
- Sanitization is layered: XML tagging, regex, optional ML classifier and output
  anomaly scan.
- Redaction must happen before persistence/export, not only before user display.
- URL previews stay disabled until an isolated fetcher design exists.
