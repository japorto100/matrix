# exec-blocking: Externe Blocker + strategisch verschobene Punkte (C)

**Zweck:** Sammelstelle fuer Tasks, die aktuell **extern blockiert** sind oder bewusst **nicht sinnvoll** sind, sie in die aktiven Slices einzumischen.  
**Regel:** In den eigentlichen `exec*` Slices stehen nur implementierbare Code-Tasks + normale Verify-Gates. Alles was hier landet, wird dort nur noch **verlinkt**.

---

## C1. Matrix: Encrypted State Events (MSC3414/MSC4362) — wartet auf Tuwunel

- **Quelle**: `exec2-01-matrix-chat-core.md` (C-4), `exec2-02-protocol-infra.md`, `exec2-04-verify-gates.md`
- **Warum blockiert**: Homeserver/Tuwunel Support fehlt; im SDK vorbereitet.
- **Trigger zum Wiederaufnehmen**:
  - Tuwunel changelog/release bestaetigt MSC3414/MSC4362 Support, oder
  - wir entscheiden, die Funktion auf Serverseite zu emulieren (nur falls protokollkonform moeglich).
- **Verify-Gates (wenn wieder aktiv)**:
  - `enableEncryptedStateEvents: true` aktiviert
  - Encrypted State Events funktionieren ohne Decrypt-Fehler in Client + Bot

---

## C2. Matrix: OIDC/MAS Auth — Legacy SSO, MAS inkompatibel (Portierungsthema)

- **Quelle**: `exec2-02-protocol-infra.md`, `exec2-04-verify-gates.md`
- **Warum blockiert**: MAS nicht kompatibel, nur Legacy SSO evaluiert; konkrete Zielarchitektur/Serverpfad unklar.
- **Trigger**:
  - MAS Support in Tuwunel, oder
  - klares Portierungsziel (z.B. anderer HS / Proxy).
- **Verify-Gates**:
  - OIDC Login Flow stabil, Token refresh, logout, und Appservice Auth sauber

---

## C3. Federation + Prod-Security Runbook (erst bei Deployment)

- **Quelle**: `exec2-04-verify-gates.md` Sektion "Federation + Security"
- **Warum blockiert**: braucht echte Domain/DNS/TLS + Prod-Setup.
- **Trigger**:
  - Entscheidung "federation on" oder "private-only" + Prod-Domain vorhanden.
- **Verify-Gates** (aus `exec2-04`):
  - `allow_federation = true` gesetzt (falls gewollt)
  - DNS `_matrix._tcp` SRV oder `.well-known/matrix/server`
  - HTTPS + echte Domain
  - Anti-Spam Bot (Draupnir/Mjolnir), ACLs, invite-policy, Directory hidden

---

## C4. E2EE Architektur-Entscheidung: Multi-Agent Skalierung

- **Quelle**: `exec-05-nats-e2ee-pipeline.md` (Architektur-Entscheidung A/B/C/D), `exec-05c-agent-isolation.md`
- **Status**: Option A aktiv. Hybrid (Option C) als Zukunftsoption dokumentiert.
- **Warum hier**: Endgueltige Entscheidung ob Per-Agent E2EE (Option B/C) noetig wird,
  haengt von Produktionsanforderungen ab (1000+ User Szenario, Compliance).
- **Trigger zum Wiederaufnehmen**:
  - Multi-Tenant Deployment geplant, oder
  - Security Audit fordert Per-Agent Crypto-Isolation
- **Verify-Gates (wenn wieder aktiv)**:
  - vodozemac-python evaluiert + getestet
  - Per-Agent Crypto-Store funktioniert
  - NATS Subject-Routing (exec-05c) als Voraussetzung verifiziert

---

## C5. Tuwunel v1.6 Upstream Bugs — Tracking (Stand 11.04.2026)

- **Quelle**: `exec2-03b-advanced-matrix-options.md` (Section 6), `exec2-04-verify-gates.md` (J7)
- **Warum hier**: Upstream-Bugs die wir nicht selbst fixen koennen. Workarounds in unserem Code wo moeglich, sonst warten.
- **Trigger**: Tuwunel v1.6.0 stable Release oder Patch-Releases die diese Issues fixen.

| Bug | Severity | Unser Workaround | Status |
|---|---|---|---|
| [#411](https://github.com/matrix-construct/tuwunel/issues/411) S3 Large File Timeout | CRITICAL | `max_request_size ≤ 100 MB` | Blockiert J5 (max_request_size erhoehen) |
| [#401](https://github.com/matrix-construct/tuwunel/issues/401) Appservice /whoami device_id | HIGH | Pruefen ob mautrix-go betroffen; ggf. device_id aus lokaler Config | Offen, Test bei Go-Appservice-Integration |
| [#377](https://github.com/matrix-construct/tuwunel/issues/377) device_lists.changed fehlt in /sync | MEDIUM | `FetchKeys()` Workaround in `go-appservice/internal/crypto/machine.go:EnsureSession()` | ✅ Proaktiv gefixt |
| [#372](https://github.com/matrix-construct/tuwunel/issues/372) /room_keys/version 500 statt 404 | LOW | Pruefen ob mautrix-go 500 korrekt handled | Offen, Test bei Go-Appservice-Integration |

---

## C6. exec2-03b Future Features — Account-Provisioning + BYOS (Backlog)

- **Quelle**: `exec2-03b-advanced-matrix-options.md` (Phase A/B/C)
- **Warum hier**: Grosse Feature-Bloecke die eigene Exec-Sessions brauchen und von mehreren Abhaengigkeiten blockiert sind.
- **Trigger**: exec2-01 (Matrix Chat Core) abgeschlossen + exec-merge-chat (Hauptprojekt-Integration) + OIDC/MAS auf Tuwunel verfuegbar.

**Phase A: Auto-Create (Minimum Viable)**
- A1: OIDC/MAS Integration (blockiert durch C2 oben)
- A2: Post-Login Matrix Init (initMatrixClient, Cross-Signing Bootstrap)
- A3: Onboarding Wizard (optional)

**Phase B: BYOS (Bring Your Own Server)**
- B1: Server-Auswahl UI (Homeserver URL + Well-Known Discovery)
- B2: Federation Verify (blockiert durch C3 oben)
- B3: E2EE Key Management UI

**Phase C: Multi-Account** (erst bei echtem Bedarf)
- C1: Mehrere Matrix-Accounts gleichzeitig + Account-Switcher

**Verify-Gates** bleiben in `exec2-04-verify-gates.md` (Gates A/B/C) — werden erst aktiv wenn die entsprechende Phase gestartet wird.
