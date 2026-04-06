# Agent Security -- Capability, Retrieval, Tooling, Storage

> **Stand:** 13. Maerz 2026
> **Zweck:** Arbeitsdokument fuer die Sicherheitsarchitektur agentischer
> Laufzeitpfade. Definiert die praktischen Leitplanken fuer Retrieval Broker,
> Tool Proxy, Capability Envelope, Agentic Storage und Security-Evaluation.
> **Abgrenzung:** `specs/AUTH_SECURITY.md` und `specs/security/*.md` bleiben
> Security-Source-of-Truth fuer produktive Regeln. Dieses Dokument ist die
> arbeitsnahe Bruecke von Agent-Design zu spaeteren Specs/Execution-Slices.
> **Primaer betroffen:** `AGENT_ARCHITECTURE.md`, `AGENT_TOOLS.md`,
> `CONTEXT_ENGINEERING.md`, `MEMORY_ARCHITECTURE.md`,
> `specs/security/POLICY_GUARDRAILS.md`

---

## Inhaltsverzeichnis

1. [Warum eigenes Agent-Security-Doc?](#1-warum-eigenes-agent-security-doc)
2. [Leitprinzipien](#2-leitprinzipien)
3. [Retrieval Broker als Pflichtpfad](#3-retrieval-broker-als-pflichtpfad)
4. [Tool Proxy + Capability Envelope](#4-tool-proxy--capability-envelope)
5. [Agentic Storage Write-Path](#5-agentic-storage-write-path)
6. [Evidence-Completeness Gates](#6-evidence-completeness-gates)
7. [Security-Evals als Dauer-Gates](#7-security-evals-als-dauer-gates)
8. [Contextual Security als Pflichtschicht](#8-contextual-security-als-pflichtschicht)
9. [Identity, Delegation und Access Mediation](#9-identity-delegation-und-access-mediation)
10. [Credential- und Secret-Management](#10-credential--und-secret-management)
11. [Information Flow Control und Taint-Pfade](#11-information-flow-control-und-taint-pfade)
12. [Priorisierte Einfuehrungsreihenfolge](#12-priorisierte-einfuehrungsreihenfolge)
13. [Querverweise](#13-querverweise)

---

## 1. Warum eigenes Agent-Security-Doc?

Agentische Systeme scheitern selten nur am Modell. Der Haupt-Risikohebel liegt in:

- falschem Kontextzugriff (Retrieval/Scope)
- ueberbreiten Tool-Rechten (Excessive Agency)
- unkontrollierten Writes (Storage/Mutation)
- fehlenden Regressionstests fuer Injection/Leakage/Misuse

Dieses Dokument macht die Runtime-Sicherheitsgrenzen fuer Agenten explizit, bevor
die Regeln in Specs und Execution-Slices gehoben werden.

---

## 2. Leitprinzipien

1. **Intelligenz != Autoritaet**
   - Agenten analysieren/planen.
   - Deterministische Backend-Schichten autorisieren und fuehren aus.
2. **Least privilege by default**
   - Kein Agent mit globalen Tool-Rechten.
   - Rechte sind task- und zeitgebunden.
3. **Read und write strikt trennen**
   - Retrieval-Pfade sind nicht automatisch Mutationspfade.
4. **Evidence first**
   - Kritische Aussagen/Actions muessen nachvollziehbare Evidenz tragen.
5. **Policy before convenience**
   - Kein direkter Tool- oder Storage-Zugriff aus dem Agent ohne Proxy/Policy.

---

## 3. Retrieval Broker als Pflichtpfad

Der Agent liest Kontext nicht direkt aus beliebigen Stores, sondern ueber einen
Broker mit harten Kontrollen:

- ACL/Tenant-Scope vor Retrieval
- Sensitivity Labels (doc/chunk)
- Source-Trust und Provenance-Pflicht
- Risk- und Class-Filter pro Task-Typ
- Query-Normalisierung und Injection-Hygiene
- explizite Trennung `instruction` vs `data`

**Arbeitsregel:**

`Agent -> Retrieval Broker -> (KG/Vector/Episodic/Docs)`

Kein direkter Agent-Zugriff auf Rohquellen als Produktionspfad.

---

## 4. Tool Proxy + Capability Envelope

Jeder Tool-Call laeuft ueber einen Proxy mit maschinenlesbarer Capability Envelope.

### 4.1 Envelope-Minimum

- `agent_class`
- `allowed_tools`
- `allowed_actions` (`read`, `write`, `delete`, `execute`)
- `risk_level`
- `required_scope`
- `budget_class`
- `needs_human_approval`
- `expiry` / `jit_token`

### 4.2 Runtime-Regeln

- Tool-Calls ohne gueltige Envelope werden abgelehnt.
- High-risk Actions brauchen zustandsabhaengige Freigabe.
- Alle Entscheidungen werden auditierbar protokolliert.

---

## 5. Agentic Storage Write-Path

Agenten schreiben nicht direkt in kanonische Wahrheitsschichten.

### 5.1 Zustaende

`draft -> review -> approved -> published`

### 5.2 Mutationsregel

- append-first/versioned statt silent overwrite
- destructive ops nur mit explizitem Policy-Hit + Audit
- provenance je Artefaktversion

### 5.3 Pflichtfelder pro Write

- actor/agent id
- task id / intent
- source/evidence refs
- previous version hash
- policy decision id
- timestamp

---

## 6. Evidence-Completeness Gates

Gegen silent retrieval failure reicht "es wurde etwas gefunden" nicht.

Pflichtfragen je kritischer Antwort/Aktion:

- Welche Source-Klassen wurden abgefragt?
- Welche Pflichtquellen fehlen?
- Gibt es Widerspruchssuche?
- Reicht die Evidenzdichte fuer den Claim?
- Muss das System abstainen statt raten?

Fehlende Pflichtabdeckung senkt Confidence oder blockiert Action-Pfade.

---

## 7. Security-Evals als Dauer-Gates

Agent Security braucht laufende Regression, nicht nur einmalige Hardening-Runden.

### 7.1 Mindest-Evalfamilien

- prompt injection
- tool misuse / confused deputy
- data leakage / over-retrieval
- policy bypass / scope escalation
- unsafe output handling

### 7.2 Betriebsgate

Neue Agent- oder Tool-Slices gehen nur live, wenn die relevanten Security-Evals
in der Zielkonfiguration reproduzierbar bestehen.

---

## 8. Contextual Security als Pflichtschicht

Neben klassischer Confidentiality/Integrity/Availability braucht der Agent eine
eigene Kontext-Sicherheitsregel:

- der Agent darf nur Kontextelemente verwenden, die zum aktiven Task gehoeren
- `system > policy > user intent > retrieved data > tool result` ist eine feste
  Prioritaetskette
- Daten duerfen keine versteckten Instruktionen einschleusen (`instruction != data`)
- Kontextwechsel (`task pivot`) erzwingt Re-Validation statt stiller Weiterfuehrung

**Arbeitsregel:**

Jeder kritische Tool-Call enthaelt einen maschinenlesbaren
`context_integrity_check` mit:

- `task_id`
- `allowed_context_classes`
- `blocked_context_classes`
- `justification`
- `policy_decision_id`

Ohne gueltigen Check keine Ausfuehrung.

---

## 9. Identity, Delegation und Access Mediation

Access Control braucht fuer Agenten klare Identitaeten und Delegation:

- **user identity:** wer den Auftrag erteilt hat
- **agent identity:** welche Agent-Instanz handelt
- **task identity:** kurzlebige Ausfuehrungsidentitaet pro Task

Delegation ist standardmaessig:

- scoped (nur noetige Rechte)
- time-bound (Ablaufzeit)
- revocable (Kill/Invalidate)
- auditierbar (wer hat wann was delegiert)

**Complete Mediation:**

Jeder Zugriff auf Tool, Speicher, Connector oder externes Ziel muss den gleichen
Policy-Entscheidpfad durchlaufen. Kein "trusted fast lane".

---

## 10. Credential- und Secret-Management

Secrets sind kein Agent-Kontext und kein normaler ENV-Transportpfad.

Pflichtregeln:

- keine unverschluesselten API-Keys/Passwoerter im Prompt oder in Logs
- keine dauerhaften High-Privilege-Credentials direkt beim Agent
- bevorzugt kurzlebige Tokens (`jit_token`, session-scoped)
- Secrets nur ueber Vault-/Broker-Schnittstelle beziehen
- Ausgabe-/Tool-Args mit Secret-Redaction vor Persistenz/Audit

Minimalvertrag je Secret-Zugriff:

- `secret_ref` statt Klartext
- `scope`
- `ttl`
- `purpose`
- `issued_to` (task/agent)

---

## 11. Information Flow Control und Taint-Pfade

Untrusted Inputs muessen ueber den gesamten Lauf als tainted markiert bleiben.

Mindestens drei Labels:

- `trusted`
- `untrusted`
- `sensitive`

Pflichtpruefungen:

- `untrusted -> execute/write/delete` nur nach Guardrail-Entscheid
- `sensitive -> external sink` standardmaessig blockieren
- transitive taint propagation ueber Retrieval, Tool-Resultate und Replans

Audit-Mindestdaten pro Flow-Entscheid:

- source label
- sink class
- decision (`allow|deny|sanitize|human_approval`)
- rule id

### 11.1 Sofort umsetzbare Security-Gates fuer Token-/KV-Caching

1. **Cache-Scope hart trennen**
   - kein Cross-User-/Cross-Tenant-Reuse ohne identische Security-Kontexte.

2. **Prompt- und Tool-Signatur in Cache-Key aufnehmen**
   - verhindert falsches Reuse nach Policy-/Template-/Tool-Aenderungen.

3. **Sensitive-Daten niemals als reusable Prefix cachen**
   - sensible Abschnitte markieren und aus sharebaren Cache-Pfaden ausschliessen.

4. **KV-Quantisierung nur mit Guardrail-Checks kombinieren**
   - bei Genauigkeitsabfall in kritischen Pfaden auf konservativeres Profil zurueckschalten.

5. **Audit-Pflicht fuer Cache-Entscheidungen**
   - `cache_hit`, `cache_miss`, `cache_bypass_reason`, `policy_decision_id` loggen.

Technische Referenzen:

- [vLLM Prefix Caching](https://docs.vllm.ai/en/stable/design/prefix_caching.html)
- [vLLM Hybrid KV Cache Manager](https://docs.vllm.ai/en/stable/design/hybrid_kv_cache_manager/)
- [SGLang Quantized KV Cache](https://docs.sglang.io/advanced_features/quantized_kv_cache.html)

---

## 12. Priorisierte Einfuehrungsreihenfolge

1. Retrieval Broker als erzwungener Pfad
2. Tool Proxy + Capability Envelope
3. Agentic Storage Write-Path mit versionierter Publish-Grenze
4. Evidence-Completeness Gates fuer kritische Flows
5. Contextual-Security + Complete-Mediation Regeln in alle kritischen Pfade
6. Credential-Vault + JIT-Token statt statischer Secrets
7. IFC/Taint-Pfade fuer Tool- und Output-Sinks
8. Security-Evals dauerhaft in Verify-Gates integrieren

---

## 13. Querverweise

- `AGENT_ARCHITECTURE.md` (Planner/Executor/Replanner + Rollen)
- `AGENT_TOOLS.md` (Toolfamilien und Zugriffspfade)
- `AGENT_HARNESS.md` (Harness-Governance, OpenSandbox, Runtime-Guardrails)
- `AGENT_MODEL_TOKEN_TUNING.md` (LLM/KV/Cache-Tuning mit Security-Gates)
- `RAG_GRAPHRAG_STRATEGY_2026.md` (Hybrid Retrieval, Query-Modi, UQ-Strategie)
- `CONTEXT_ENGINEERING.md` (Context Assembly und Retrieval-Policies)
- `MEMORY_ARCHITECTURE.md` (Memory-Tiering und Artefaktlayer)
- `specs/AUTH_SECURITY.md` (Security-Umbrella)
- `specs/security/POLICY_GUARDRAILS.md` (Policy-Gates)
- `specs/security/SECURITY_HARDENING_TRACKS.md` (Hardening-Reihenfolge)
- `specs/execution/agent_security_runtime_delta.md` (Execution-Owner)
