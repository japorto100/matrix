# exec-eval: Infra-/Umgebungsabhaengige Verify + Evaluation Workpacks

**Zweck:** Sammelstelle fuer Items, die **code-seitig groesstenteils vorhanden** sind, aber
deren Abschluss **Infra/Accounts/Secrets/Runtime** oder eine **explizite Evaluation/Decision**
braucht. Damit bleiben die eigentlichen `exec-*` Slices frei von wiederkehrenden "blocked/eval" Hinweisen.

> Regel: Neue Items zuerst hier parken, wenn sie ohne Setup nicht sinnvoll verifizierbar sind.

---

## EVAL-01: Matrix Chat Verify Gates (DevStack / 2nd Client / Element X)

**Quelle:** `exec2-04-verify-gates.md` (Abschnitte A–H)  
**Typ:** Infra/Runtime Verify (nicht primär Coding)  
**Voraussetzungen:**
- laufender Tuwunel Homeserver + Sliding Sync
- `nextjs-chat` laeuft
- optional: 2. Client (Element X Mobile/Desktop) fuer Interop
- LiveKit + lk-jwt-service fuer Calls

### Verify Gates (Auszug / normative Quelle bleibt exec2-04)
- **A1/A2/A3/A4**: Homeserver/SlidingSync/LiveKit/Env korrekt
- **B1–B4**: E2EE / Cross-Signing / Key Backup / MSC4381
- **C–H**: Chat Core + Advanced Features + Shortcuts + optional Blur

**Done:** Checkliste aus `exec2-04` soweit wie moeglich abgehakt, Evidence (Logs/Screenshots) verlinkt.

---

## EVAL-02: exec-05 A4 (NATS E2E Test)

**Quelle:** `exec-05-nats-e2ee-pipeline.md` (A4 + Gate 1/2)  
**Typ:** Runtime Verify (NATS + Go + Python + LLM Mock)  
**Voraussetzungen:**
- NATS laeuft (ggf. JetStream)
- Go Appservice laeuft & ist bei Tuwunel registriert
- Python Bridge laeuft & subscribed
- Agent Service / LLM Mock erreichbar

### Verify Gates
- User → Matrix → Go → NATS → Python → Agent → NATS → Go → Matrix klappt

**Done:** A4 + Gate 1/2 in exec-05 abgehakt, inkl. Log evidence.

---

## EVAL-03: exec-06 Phase 2/3/4 Verify (Agent Chat E2E + Voice + Frontend SOTA Verify)

**Quelle:** `exec-06-agent-chat-integration.md`  
**Typ:** E2E Verify (Backend + UI + optional Voice)  
**Voraussetzungen:**
- Go Gateway `/api/v1/agent/*` laeuft
- Python Agent laeuft
- (optional) API Keys fuer echten LLM Provider oder Mock-Agent Mode
- LiveKit fuer Voice Verify

### Verify Gates
- `/api/v1/agent/chat` proxied SSE funktioniert
- Tool approval flow end-to-end
- Voice: STT→LLM→TTS latency gate (nur runtime)
- Frontend SOTA: shiki/motion/auto-animate etc. ohne errors

**Done:** Gate-Checklist in exec-06 abgehakt + Evidence.

---

## EVAL-04: exec-11 Memory Verify (LLM Key / Postgres)

**Quelle:** `exec-11-memory-evolution.md` (Gate 1/2/3/5/6/7)  
**Typ:** E2E Verify (DB + LLM)  
**Voraussetzungen:**
- `HINDSIGHT_DB_URL` auf funktionierendes Postgres+pgvector
- LLM Provider Key (z.B. `ANTHROPIC_API_KEY`) fuer retain/reflect flows

### Verify Gates (Auszug)
- retain/recall/reflect/consolidation E2E
- orchestrator memory sharing E2E
- conflict detection E2E

**Done:** Gates abgehakt + Evidence.

---

## EVAL-05: exec-05b Messaging Bridges (Accounts + External Platforms)

**Quelle:** `exec-05b-messaging-bridges.md`  
**Typ:** External platform integration + runtime verify  
**Voraussetzungen:**
- Accounts/Devices (WhatsApp/Signal/Telegram/Meta/Discord)
- mehrere Appservice registrations in Tuwunel
- NATS+Go+Python pipeline stabil (exec-05 Gate 1/2)

### Verify Gates
- Bridge ↔ Matrix ↔ Agent pipeline pro Platform

**Done:** Gates pro Bridge erfuellt, Setup dokumentiert.

