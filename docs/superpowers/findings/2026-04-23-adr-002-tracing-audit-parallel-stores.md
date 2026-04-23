# ADR-002 — Tracing (agent.spans) und Audit (agent.audit_events) bleiben parallel

**Date:** 2026-04-23
**Status:** Decided — kein Merge; minimaler cross-write-cleanup
**Predecessor:** `specs/execution/exec-blocking.md §C9` (Entscheidung "nicht mergen" bereits getroffen 2026-04-20)
**Owner-spec:** `specs/execution/exec-17-observability-harness-traces.md`
**Umbrella:** `specs/execution/exec-security.md §3` (audit-trail integrity)

---

## Context

matrix betreibt **zwei parallele Observability-Stores**:

| Store | Modul | Schema | Retention | Consumer | Purpose |
|---|---|---|---|---|---|
| **Tracing** | `agent/tracing.py` | `agent.spans` JSONB | 30 Tage | OpenObserve, Grafana, Langfuse (Fan-Out geplant) | Performance-Debug, Latenz, Token-Flow, Fitness-Regression |
| **Audit** | `agent/audit/` | `agent.audit_events` | 1 Jahr | Control-UI `AuditTab`, Ops-Review, Compliance | Append-only trail, User-Content, Consent-Decisions, Sandbox-Executions |

Am 2026-04-20 wurde in `exec-blocking.md §C9` entschieden: **nicht mergen**. Die beiden haben unterschiedliche Consumers, Retention-Policies und Query-Patterns. Dieser ADR **dokumentiert die Entscheidung formell** und legt fest, welche konkreten cross-writes redundant sind.

## Die eigentliche Frage: welche `AuditAction` sind redundant zu Tracing-Spans?

| Action | Emit-Stelle | Tracing-Span enthält | Audit-Content-Payload | Verdict |
|---|---|---|---|---|
| `LLM_REQUEST` | `llm_node.py:184` | `turn_span("llm_call")` mit `model`, `iteration`, `llm.routing_reason/used/picked`, `tool_count` implizit über tool-spans | nur `model` + `tool_count` in metadata | **REDUNDANT → entfernen** |
| `LLM_RESPONSE` | `llm_node.py:413` | gleicher span + `llm.token_usage.*`, `llm.cost_usd`, `llm.cost_source`, `agent.reasoning.*` | **speichert `input_data` + `output_data` bis 2000 chars** (message-content) | **BEHALTEN — content für 1y compliance** |
| `TOOL_CALL` | `tool_node.py:159`, `extensions.py:91` | `tool_span` mit `tool.name`, `tool.iteration` | speichert `input_data` (tool-args) | **BEHALTEN — tool-inputs compliance-relevant (sandbox, trading-orders, memory-writes)** |
| `TOOL_RESULT` | `tool_node.py:140/181/208/231`, `extensions.py:101` | gleicher span + `tool.duration_ms`, `tool.success` | speichert `output_data` | **BEHALTEN — analog TOOL_CALL** |
| `MEMORY_*` | `memory_node.py` | separate memory-spans | speichert recall/retain content | **BEHALTEN — content** |
| `CONSENT_REQUEST`, `CONSENT_DECISION` | `consent/`, `approval_node.py` | span markiert Consent-Punkte | speichert Consent-Entscheidung + Reason | **BEHALTEN — compliance primary** |
| `RATE_LIMIT_HIT` | `consent/__init__.py` | span emits bucket-id | metadata nur | **BEHALTEN — throttling audit** |
| `SANDBOX_EXEC` | `tools/file_analyze.py`, `sandbox/manager.py` | span mit sandbox-id | tool-args + result | **BEHALTEN — sandbox escapes** |
| `SKILL_*` | `skills/loader.py` | span mit skill-name | metadata nur | **BEHALTEN — skill-loader audit** |

**Key distinction:** Tracing speichert **wie** (performance/flow), Audit speichert **was** (content/decisions). Sobald ein Event keinen content trägt und der Tracing-Span das gleiche Signal schon hat → redundant.

## Decision

1. **Parallel-Architektur bleibt.** Kein Merge geplant — unterschiedliche Retention + Consumer + Privacy-Posture (Tracing darf zu OpenObserve/external, Audit bleibt intern).
2. **`LLM_REQUEST` wird aus `llm_node.py` entfernt** (~10 LOC). Redundant: span trägt `model`, `iteration` und `tool_count` ergibt sich aus parallel tool-spans oder kann als span-attribute ergänzt werden.
3. **`LLM_RESPONSE`, `TOOL_CALL`, `TOOL_RESULT` bleiben vorerst in Audit.** Sie speichern content-payloads die für 1-Jahr-Compliance relevant sind (user-query + agent-response trail, tool-inputs/outputs für sensitive tools).
4. **Future-cleanup TODO (nicht jetzt):** per-tool `audit_required: bool` Flag in der TradingTool-ABC. Tools ohne Compliance-Relevanz (pure-read, idempotent, non-sensitive) setzen es auf `False`; `TOOL_CALL`/`TOOL_RESULT` wird dann konditional geschrieben. Cross-Ref: `exec-security.md §2` (skills-guard HITL-decision) soll das als Teil der sensitive-tool-klassifikation miterledigen.
5. **Span-attribute Ergänzung:** `llm_node.py` fügt `agent.tool_count` als span-attribute hinzu, damit die entfernte audit-metadata weiterhin in Tracing greifbar ist.

## Consequences

**Positive:**
- ~10 LOC weniger double-write pro LLM-call. DB-load von `agent.audit_events` sinkt bei LLM-heavy runs um die Hälfte der LLM-events (LLM_REQUEST entfiel).
- Klarere Semantik: Audit-Events signalisieren "dies ist content du für 1y behalten willst"; Tracing signalisiert "dies ist ein performance/flow-Signal".
- `agent.audit_events` table wächst langsamer → Control-UI AuditTab bleibt performant.

**Negative:**
- `TOOL_CALL`/`TOOL_RESULT` bleiben weiterhin double-write. Der future-cleanup braucht sensitive-tool-Klassifikation (unabhängige arbeit in `exec-security`).
- Bei einem hypothetischen future "replay LLM call" Feature würde `LLM_REQUEST` audit-log fehlen — aber der request-content ist implizit im `LLM_RESPONSE.input_data` (letzte user-message), und `messages[]` state liegt zu dem Zeitpunkt im Graph.

**Neutral:**
- Audit-schema unverändert — `LLM_REQUEST` als Enum-Variante bleibt (für historische Daten + zukünftigen Re-Use wenn sich Compliance-Anforderung ändert).
- Fallback: falls Compliance später `LLM_REQUEST` doch als audit-log benötigt, 1 Zeile reaktivieren.

## Implementation

- `python-backend/agent/graph/nodes/llm_node.py`: remove `audit_log(AuditAction.LLM_REQUEST, ...)` call block; add `span.set_attribute("agent.tool_count", len(tool_defs))` vor dem LLM-call.
- Audit enum `LLM_REQUEST` bleibt im code (für historische rows + potential rollback).
- Tests: existing suite keep passing; no new tests needed for removal (negative assertion "wird nicht mehr geloggt" ist schwer stabil zu machen gegen den fire-and-forget path).
- Exec-17 spec cross-ref aktualisieren: Link auf diesen ADR im Teaser-Abschnitt.

## Out of scope

- `TOOL_CALL`/`TOOL_RESULT` cleanup (braucht sensitive-tool-Klassifikation in `exec-security`)
- Audit-chain HMAC integrity (exec-security §3.2 Phase-C+)
- Per-span redaction enforcement (exec-security §1.4, eigener Track)

## Changelog

| Datum | Event |
|---|---|
| 2026-04-20 | Entscheidung "parallel halten, nicht mergen" in `exec-blocking.md §C9` festgehalten |
| 2026-04-23 | Dieser ADR — formelle Dokumentation + `LLM_REQUEST` Removal als konkreter cross-write-cleanup |
