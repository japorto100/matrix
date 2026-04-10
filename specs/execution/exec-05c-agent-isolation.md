# exec-05c: Agent-Isolation (NATS Routing, Key Deletion, Hybrid E2EE)

**Datum:** 10.04.2026
**Status:** Geplant
**Abhaengig von:** exec-05 Phase A+B (NATS + E2EE) ✅ — muessen verifiziert sein (EVAL-02)
**Herkunft:** Extrahiert aus exec-05 Phase C + Architektur-Entscheidungen (10.04.2026)

---

## Warum

exec-05 ist "code complete" (Phase A+B). Phase C (Agent-Isolation) und die E2EE-Architektur-Vorbereitung
sind eigenstaendige Arbeit die erst bei Multi-Agent-Betrieb relevant wird. Darum eigener Slice.

**E2EE-Entscheidung (10.04.2026):**
- Option A (Zentrales Go Gateway) ist aktiv und implementiert
- Option C (Hybrid) wird als Zukunftsoption vorbereitet (Interface, nicht Logik)
- Option B (Per-Agent E2EE) bleibt evaluierbar, aber nicht implementiert

---

## Phase 1: NATS Subject-Routing (deaktiviert)

ENV: `NATS_SUBJECT_ROUTING_ENABLED=false` (default)

- [x] **C1:** NATS-Subjects per Raum partitionieren ✅ (10.04.2026)
  - `NATS_SUBJECT_ROUTING_ENABLED=false` (default deaktiviert)
  - Bei `true`: `matrix.message.inbound.room.<roomID>` statt globalem Subject
  - Fallback auf globalen Subject wenn deaktiviert
  - Python Bridge subscribed nur auf Raeume die ihr Agent bedient (TODO: Python-Seite)

- [x] **C2:** Agent-Routing im Go Appservice ✅ (10.04.2026)
  - `extractAgentName()` in `server.go` extrahiert Agent-Name aus @agent-* Mention
  - NATS Subject: `matrix.message.inbound.agent.<name>` (bei Subject-Routing aktiv)
  - `InboundMessage.TargetAgent` Feld fuer Python-Seite
  - golangci-lint: 0 issues

- [ ] **C3:** Access Control auf NATS
  - NATS Authorization: Python-Trading darf nur `matrix.message.trading` lesen
  - Verhindert dass ein Agent-Service andere Agents' Nachrichten sieht

- [x] **C4:** Agent Thread-Support ✅ (10.04.2026)
  - `InboundMessage.ThreadID` + `IsThreadReply` Felder fuer Thread-Kontext
  - Go erkennt `RelatesTo.Type == RelThread` in eingehenden Events
  - `ReplyMessage.ThreadRootID` Feld fuer Thread-Replies vom Agent
  - `handleAgentReply()` setzt `m.relates_to` mit `rel_type: m.thread`
  - `AgentSender.SendContent()` neue Methode fuer strukturierte Events
  - E2EE Thread-Replies via `sendEncryptedReply()` (nimmt jetzt MessageEventContent)
  - golangci-lint: 0 issues

---

## Phase 2: Key Deletion Config

- [x] **KD-1:** Config-Flag `MATRIX_DELETE_KEYS_AFTER_DECRYPT` im Go Crypto-Store ✅ (10.04.2026)
  - Default: `false` (Keys bleiben — Agent braucht History-Kontext)
  - `true`: Megolm Session Key wird nach Decrypt redacted (Forward Secrecy)
  - Kompromiss-Option: `MATRIX_DELETE_KEYS_AFTER_HOURS=24` (Config vorhanden, Logik TODO)

- [x] **KD-2:** Implementierung in `crypto/machine.go` ✅ (10.04.2026)
  - `RedactGroupSession()` nach erfolgreichem Decrypt (mautrix API)
  - Logging: "E2EE: key redacted after decrypt (Forward Secrecy)"
  - Key Backup File wird NICHT betroffen (separate Logik)
  - golangci-lint: 0 issues

---

## Phase 3: Hybrid-Interface Vorbereitung (Option C Struktur)

- [x] **HY-1:** Agent-Capability Registration in Go Appservice ✅ (10.04.2026)
  - Config-Feld: `AgentCapabilities` string in `config.go` (`MATRIX_AGENT_CAPABILITIES`)
  - Default: `"gateway"` (Option A — Go entschluesselt)
  - Spaeter erweiterbar zu Map/JSON fuer Per-Agent Capabilities

- [x] **HY-2:** Conditional Decrypt im Go Event-Handler ✅ (10.04.2026)
  - `handleEncrypted()` prueft `cfg.AgentCapabilities`
  - `"gateway"` (default) → Go entschluesselt wie bisher
  - `"native"` → Log + TODO-Marker (Ciphertext-Forwarding nicht implementiert, Fallback auf Decrypt)
  - Nur Routing-Logik, KEIN eigener Crypto-Store fuer Agent implementiert

- [ ] **HY-3:** vodozemac-python Evaluation (spaeter)
  - Reife-Check: vodozemac-python v0.9.0+ testen
  - Soatok Feb 2026 Issues bewerten (all-zero X25519, truncated MACs)
  - Nur relevant wenn Option C aktiviert werden soll

---

## Verify-Gates

### Gate 1: NATS Subject-Routing
- [ ] `NATS_SUBJECT_ROUTING_ENABLED=true` → Subjects per Agent partitioniert
- [ ] Agent-Routing: Mention → korrektes NATS Subject
- [ ] NATS Authorization Rules (Agent darf nur eigenes Subject lesen)
- [ ] Agent Thread-Support: Thread-Mention → Thread-Reply

### Gate 2: Key Deletion
- [ ] `MATRIX_DELETE_KEYS_AFTER_DECRYPT=true` → Keys nach Decrypt geloescht
- [ ] `MATRIX_DELETE_KEYS_AFTER_DECRYPT=false` → Keys bleiben (Default)
- [ ] Key Backup File nicht betroffen

### Gate 3: Hybrid-Interface
- [ ] Agent-Capability `"gateway"` → Go entschluesselt (bestehendes Verhalten)
- [ ] Agent-Capability `"native"` → Ciphertext durchgereicht
- [ ] Default = `"gateway"` fuer alle Agents

---

## Risiken

| Risiko | Mitigation |
|---|---|
| NATS Subject-Explosion bei vielen Raeumen | JetStream mit Wildcard-Subjects + TTL |
| Key Deletion bricht Agent-History | Default OFF, Config-Flag |
| Hybrid erhoet Komplexitaet | Nur Interface vorbereitet, keine Logik aktiv |

---

## Abhaengigkeiten

- exec-05 Phase A+B verifiziert (EVAL-02)
- exec-10 Multi-Agent Orchestrierung (fuer Multi-Agent Testing)
- Fuer Phase 3 HY-3: vodozemac-python stabil
