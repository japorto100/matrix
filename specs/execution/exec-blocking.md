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
