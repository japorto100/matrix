# Agent Runtime Architecture

> **Stand:** 16. April 2026
> **Zweck:** kurze Owner-Spec fuer verbindliche Agent-Runtime-Grenzen,
> Orchestration-Defaults, Policy-Tiers und Memory-Write-Regeln.
> **Herkunft:** Matrix-adaptierte Root-Fassung aus
> `trading-project/docs/specs/architecture/AGENT_RUNTIME_ARCHITECTURE.md`.

---

## 1. Grundprinzip

- Agenten sind **untrusted orchestrators**, keine impliziten DB- oder Admin-Clients.
- Tool-Calls laufen nur ueber policy-gepruefte Endpunkte.
- Mutationen brauchen Scope-Pruefung, Idempotency und ggf. Approval.
- Prompt-Injection-resistente Tool-Policy: least privilege, deny-by-default,
  explizite Allowlists.

---

## 2. Verbindliches Rollenmodell

| Rolle | Technologie | Darf LLM? | Darf Scores veraendern? |
|---|---|---|---|
| Extractor | LLM | Ja | Nein |
| Verifier | LLM + Regeln | Ja | Nein |
| Deterministic Guard | Code-only | Nein | Ja |
| Synthesizer | LLM | Ja | Nein |

Der Deterministic Guard bleibt der Kern: auditierbar, reproduzierbar,
unit-testbar und nicht prompt-injectable.

---

## 3. Orchestration Defaults

### 3.1 Runtime-Entscheidung

| Ebene | Default | Wann |
|---|---|---|
| Agent-/Reasoning-Workflows | `LangGraph` | mehrstufige Agent-Laeufe, HITL, Resume |
| Produkt-/Business-Workflows | `Temporal` spaeter gezielt | langlebige, produktkritische Ablaeufe |

### 3.2 Plan-Execute-Replan

1. Planner erzeugt oder aktualisiert den Plan.
2. Executor arbeitet immer gegen einen expliziten Planstand.
3. Replanner passt den Plan nach Ergebnissen, Fehlern oder fehlender Evidenz an.

---

## 4. Memory-Write-Policy

### 4.1 Leitregel

Agenten schreiben nicht direkt in kanonische Wahrheitsschichten.

Sie duerfen:

- Claims vorschlagen
- Evidence verknuepfen
- bounded writes in klar abgegrenzten Schichten ausfuehren

Sie duerfen nicht:

- globale kanonische Fakten direkt mutieren
- User-Aussagen still zu Weltwissen promoten

### 4.2 Matrix-Uebertrag fuer Memory-Schichten

| Schicht | Default | Agentischer Pfad |
|---|---|---|
| `personal_raw` | bounded-write | Chat-/Tool-/Scratch-Evidence |
| `personal_derived` | bounded-write mit Promotion-Gates | nur mit Backlinks, Provenance, Status |
| `personal_kb` | getrennt, nicht Default-Write | nur ueber dedizierte KB-Pfade |
| `bridge_world` / `world_kg` | read-only fuer Agent-Default | kein direkter Default-Write |

### 4.3 Pflichtfelder fuer agentische Writes

- `provenance`
- `idempotency_key`
- `audit_event_id`
- `reversible` oder nachvollziehbarer Rollback-Pfad

---

## 5. Policy-Tiers

| Tier | Beschreibung |
|---|---|
| `read-only` | keine Mutation, kein Approval |
| `bounded-write` | mutierend, stark begrenzt, Policy-/Idempotency-Gates |
| `approval-write` | explizite Freigabe, strenge Auditierung |

---

## 6. Verify- und Runtime-Regeln

- jeder kritische Pfad braucht nachvollziehbare Evidenz
- Memory-/Context-Policies muessen in Runtime und Inspector sichtbar sein
- Postgres-Smokes sind gueltige harte Gates fuer backendzentrierte Slices
- echte Full-Stack-E2Es bleiben als dokumentierte Gates offen, wenn Runtime oder
  `.env` fehlen

---

## 7. Querverweise

- `AGENT_ARCHITECTURE.md`
- `AGENT_HARNESS.md`
- `AGENT_SECURITY.md`
- `CONTEXT_ENGINEERING.md`
- `MEMORY_ARCHITECTURE.md`
