# Matrix Security — Erkenntnisse & Entscheidungen

**Datum:** 27.03.2026
**Status:** Aktiv

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

## E2EE — Verschlüsselung

### Entscheidungen
- **Tuwunel Default:** `encryption_enabled_by_default_for_room_type = "off"` — Clients entscheiden pro Raum
- **Privater Raum:** E2EE an (Client sendet `m.room.encryption` bei Erstellung)
- **Offener Raum:** Kein E2EE
- **DMs (Dev):** Unverschlüsselt (Python Bridge kann nicht entschlüsseln)
- **DMs (Prod nach exec-05):** E2EE für User↔User, optional für User↔Agent
- **Agent-Räume:** Go Appservice entschlüsselt als Raum-Member, Python bekommt Klartext via NATS

### SSRF-Analogie bei E2EE
E2EE schützt ruhende Daten (DB-Leak, Backup). Ohne E2EE kann ein Server-Admin alles lesen. Mit E2EE nur die Raum-Mitglieder + Go Appservice (für Agent-Räume).

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

## XSS-Schutz

- `rehype-sanitize` mit `defaultSchema` sanitized alle HTML-Nachrichten
- `<script>`, `onerror`, `javascript:` URLs werden komplett gestripped
- `style`-Attribute nur mit Allowlist (`color`, `background-color`, `font-weight`, etc.)
- Getestet: `<script>alert("XSS")</script>` → komplett entfernt, nur Safe-Text bleibt
