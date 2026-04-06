# Matrix Security — Erkenntnisse & Entscheidungen

**Status:** Aktiv
**Stand:** 06.04.2026

> **Hinweis:** Dieses Dokument ist die **Matrix-spezifische** Security-Spec. Fuer den
> Agent-Security-Stack (Audit, Consent, Sanitizer, RBAC, Rate-Limiting) siehe
> `specs/execution/exec-12-sandbox-security.md`.

---

## URL Preview — SSRF Risiko

### Problem
Matrix Homeserver fetcht URLs server-seitig für OG-Tag Previews (`/_matrix/client/v1/media/preview_url`). Ein Angreifer kann interne Dienste über den Homeserver als Proxy erreichen:

- `http://169.254.169.254/latest/meta-data/` → AWS/GCP Credentials
- `http://localhost:8090/...` → Go Appservice interne Endpoints
- `http://127.0.0.1:4222/` → NATS
- `http://127.0.0.1:5432/` → Datenbank

### Wie andere es machen
| App | Wer fetcht | SSRF-Risiko |
|-----|-----------|-------------|
| **WhatsApp** | WhatsApp Server (Crawler) | Ja, aber Milliarden-Budget für Schutz |
| **Matrix/Synapse** | Homeserver | Ja — CVE-2023-32683 (SSRF via URL Preview) |
| **Element Web** | Homeserver via SDK `getUrlPreview()` | Per Default AUS in E2EE-Räumen |
| **Browser direkt** | Nicht möglich | CORS blockiert Cross-Origin Requests |

### Community-Empfehlung
- **Element Web**: URL Preview in E2EE-Räumen per Default deaktiviert (Privacy-Leak)
- **Synapse Docs**: "Anyone in any room could cause arbitrary GET requests to internal services"
- **Self-Hosted Klein/Privat**: Aus lassen
- **Enterprise**: An mit strikter IP-Blacklist + dediziertem Worker

### Unsere Entscheidung: AUS (Dev + Prod)
- **Begründung:** SSRF-Risiko überwiegt den kosmetischen Nutzen
- **User-Perspektive:** User klickt die URL an und sieht die Seite direkt — Preview-Karte ist Nice-to-have, nicht kritisch
- **Agent-Chat:** Agent sendet Text/Code, keine URLs die Preview brauchen
- **Zukunft:** Wenn sicherere Lösungen existieren (z.B. isolierter Fetcher-Service in eigenem Container ohne Netzwerkzugriff auf interne Dienste), kann es wieder aktiviert werden

### Config
```toml
# Dev + Prod: URL Preview deaktiviert (SSRF-Schutz)
# url_preview_domain_contains_allowlist bleibt auskommentiert = alles blockiert
# Tuwunel Default: blockiert wenn keine Allowlist gesetzt
```

### Falls später aktiviert (Prod)
```toml
# Strikte Allowlist — nur bekannte Domains
url_preview_domain_explicit_allowlist = [
    "github.com", "wikipedia.org", "youtube.com",
    "twitter.com", "x.com", "reddit.com",
    "stackoverflow.com", "medium.com",
]

# Private Netzwerke explizit blockieren
url_preview_domain_explicit_denylist = [
    "localhost", "127.0.0.1", "0.0.0.0",
    "169.254.169.254", "metadata.google.internal",
    "10.*", "172.16.*", "192.168.*",
]
```

---

## E2EE — Verschluesselung

### Entscheidungen
- **Tuwunel Default:** `encryption_enabled_by_default_for_room_type = "off"` — Clients entscheiden pro Raum
- **Privater Raum:** E2EE an (Client sendet `m.room.encryption` bei Erstellung)
- **Offener Raum:** Kein E2EE
- **DMs:** E2EE fuer User↔User, fuer User↔Agent ab exec-05 ebenfalls aktiv
- **Agent-Raeume:** Go Appservice entschluesselt als Raum-Member, Python bekommt Klartext via NATS

### Trust-Modell
Detaillierte Beschreibung in `06-e2ee.md` und `13-e2ee-agent-architecture.md`. Kurz:
- E2EE schuetzt ruhende Daten (DB-Leak, Backup)
- Ohne E2EE kann ein Server-Admin alles lesen
- Mit E2EE nur die Raum-Mitglieder + Go Appservice (fuer Agent-Raeume)
- Python Bridge braucht keine Schluessel — Go decryptet vor NATS-Publish

---

## pendingEventOrdering Bug

### Problem
matrix-js-sdk Default `pendingEventOrdering: "chronological"` crasht bei `sendEvent`, `redactEvent`, `kick`, `ban`, `leave`, `forget`, `sendReadReceipt` mit:
```
Cannot call getPendingEvents with pendingEventOrdering == chronological
```

### Lösung
```typescript
pendingEventOrdering: "detached"  // in client.ts createClient opts
```
Alle SDK-Calls funktionieren nativ. Kein fetch-Workaround nötig.

---

## Registrierung

### Dev
```toml
allow_registration = true
registration_token = "matrix-dev-token-2026"
```

### Prod
```toml
allow_registration = false  # oder true mit starkem Token
registration_token = "..."  # aus Secrets-Manager
```
User-Accounts werden programmtisch über die Admin-API erstellt (Go Backend bei Portierung).

---

## XSS-Schutz (nextjs-chat)

- `rehype-sanitize` mit `defaultSchema` sanitized alle HTML-Nachrichten
- `<script>`, `onerror`, `javascript:` URLs werden komplett gestripped
- `style`-Attribute nur mit Allowlist (`color`, `background-color`, `font-weight`, etc.)
- Getestet: `<script>alert("XSS")</script>` → komplett entfernt, nur Safe-Text bleibt
- Gilt fuer beide Komponenten-Sets: `nextjs-chat/` (Matrix Chat) und `agent-chat/` (Agent Chat)

---

## Agent-Security (exec-12 Phase 2)

Der Agent-Security-Stack ist in `specs/execution/exec-12-sandbox-security.md` dokumentiert.
Implementierung in `python-backend/agent/`:

| Komponente | Datei | Zweck |
|---|---|---|
| Audit Logging | `agent/audit/` | Structured Events (TOOL_CALL, CONSENT_DECISION, ...) → PostgreSQL/JSON Lines |
| Consent Engine | `agent/consent/` | Per-Tool Consent Levels, Session Cache, Rate Limiter |
| Sanitizer | `agent/middleware/sanitizer.py` | P0-P3 Defense (XML Tagging, Regex, ML Classifier, Anomaly Scan) |
| Template Validator | `agent/middleware/template_validator.py` | Jinja2 Injection Prevention |
| RBAC | `consent_policy.yaml` + `roles.py` | Role-based Tool Access (viewer/analyst/trader/admin) |
| Rate Limiting | `agent/consent/rate_limiter.py` | Per-Tool + Per-Session Limits, Token Budget, Iteration Limits |
| Installer Hardening | `scripts/harden-env.py` | Default-Credentials in .env durch zufaellige Tokens ersetzen |

OWASP LLM01:2025 konform: Privilege Min ✅, HITL ✅, Structural Separation ✅,
Content Tagging ✅, Filtering ✅.
