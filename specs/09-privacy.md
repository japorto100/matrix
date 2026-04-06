# Matrix Homeserver — Privacy & Metadata-Minimierung

**Status:** Aktiv
**Stand:** 06.04.2026 — Tuwunel Privacy hardened, Dendrite/Zendrite Fallback fuer Windows

## Uebersicht

Matrix-Server speichern und verarbeiten potentiell sensitive Metadaten:
- Wer mit wem kommuniziert (Raumteilnehmer)
- Wann User online sind (Presence)
- Wann Nachrichten gelesen wurden (Read Receipts)
- Welche URLs vorgeschaut wurden (URL Preview)
- IP-Adressen der Clients

Diese Spec dokumentiert alle verfügbaren Konfigurationsoptionen zur Minimierung.

---

## Vergleich: Tuwunel vs. Dendrite

| Feature | Tuwunel v1.5.1 | Dendrite v0.13 |
|---|---|---|
| **URL Preview deaktivierbar** | ✅ Granulare Allowlists | ❌ Keine Konfiguration |
| **Presence deaktivierbar** | ✅ `allow_inbound/outbound` | ⚠️ Config vorhanden, aber Read Receipts gehen trotzdem durch |
| **Read Receipts deaktivierbar** | ✅ Private Receipts nicht mehr an Federation | ❌ Known Bug #3284 — immer aktiv |
| **Message Retention** | ✅ MSC2815, Standard 60 Tage | ❌ Nicht implementiert (Issue #3330) |
| **Telemetrie/Sentry** | ✅ Standardmäßig deaktiviert | ⚠️ `/metrics` Endpoint aktiv (konfigurierbar) |
| **Logging Level** | ✅ `warn` konfigurierbar | ✅ `log_level: warn` |
| **IP Logging** | ⚠️ Wenig Dokumentation | ✅ `real_ip_header: ""` |

**Fazit:** Tuwunel für Production wenn Privacy wichtig. Dendrite nur für Windows-Dev.

---

## Tuwunel — Privacy Config (homeserver/tuwunel.toml)

### Logging
```toml
# Nur Warnungen und Fehler — keine User-Aktivität geloggt
# ACHTUNG: "warn,tuwunel=warn" ist Synapse-Syntax — funktioniert NICHT in Tuwunel
log = "warn"
```

### URL Preview — Deaktiviert (SSRF-Schutz)
```toml
# URL-Vorschau schickt URLs an den Server → Privacy + SSRF-Risiko
# Aktive Config in tuwunel.toml: leere Allowlist (= alles blockiert)
url_preview_domain_contains_allowlist = []
```
Detail zu SSRF-Risiken siehe `16-security.md`.

### Presence — Lokal aktiv, Federation deaktiviert
```toml
# Aktuelle Config (B-6 in 04-nextjs-chat): lokale Presence aktiv
# fuer UI-Anzeige (gruener Punkt in RoomList), aber keine Federation
allow_local_presence    = true    # erlaubt lokale Presence-Updates
allow_incoming_presence = false   # keine eingehenden von anderen Servern
allow_outgoing_presence = false   # eigenen Status nicht weitersenden
```

> **Hinweis:** Wenn vollstaendige Presence-Deaktivierung gewuenscht ist (z.B. fuer
> Production mit hoeheren Privacy-Anforderungen), `allow_local_presence = false`
> setzen. Das deaktiviert dann auch die UI-Indikatoren.

### Read Receipts
Tuwunel v1.5.1 leitet **private Read Receipts** nicht mehr an die Federation weiter — nur noch öffentliche. Kein extra Config-Key nötig.

### Message Retention (MSC2815)
```toml
# Standard: redaktierte Inhalte nach 60 Tagen löschen
# Spezifische Key-Namen in v1.5.1 noch nicht vollständig dokumentiert
# Gilt für redacted events (gelöschte Nachrichten)
```

### Telemetrie / Sentry
Sentry ist in Tuwunel standardmäßig deaktiviert — kein Config nötig.

### Federation deaktiviert
```toml
allow_federation = false
# → Kein Metadaten-Leak an andere Homeserver
# → Keine ausgehenden HTTP-Requests zu fremden Servern
# → Kein Cross-Server Room Directory Lookup
```

---

## Dendrite — Privacy Config (homeserver/dendrite.yaml)

### Logging
```yaml
global:
  log_level: warn   # minimal
```

### Presence deaktivieren
```yaml
global:
  presence:
    enable_inbound: false
    enable_outbound: false
```
> ⚠️ **Bekannte Einschränkung:** Read Receipts werden trotzdem gesendet (Bug #3284).
> Presence-Deaktivierung hat keinen Einfluss auf Read Receipts.

### Metriken deaktivieren
```yaml
global:
  metrics:
    enabled: false   # kein /metrics Endpoint
```
Standardmäßig aktiv — exposiert User-Counts, Message-Counts, Federation-Status.

### IP-Header nicht weiterleiten
```yaml
sync_api:
  real_ip_header: ""   # kein Real-IP aus Proxy-Headern lesen
```

### Media Cache minimieren
```yaml
global:
  cache:
    max_size_estimated: 256mb   # statt default 1gb
    max_age: 30m
```

### Federation deaktivieren
```yaml
global:
  disable_federation: true
```

### Bekannte Einschränkungen (v0.13)
- **Read Receipts:** Können nicht serverseitig deaktiviert werden (Issue #3284)
- **Message Retention:** Nicht implementiert (Issue #3330) — keine automatische Löschung
- **URL Preview:** Keine Konfigurationsoption zum Deaktivieren gefunden
- **Typing Notifications:** Keine serverseitige Deaktivierung

---

## Production-Empfehlungen

### Wenn Privacy wichtig ist → Tuwunel
1. `allow_federation = false` (lokale Isolation)
2. `url_preview_domain_contains_allowlist = []` (URL Preview deaktiviert)
3. `allow_incoming_presence = false`, `allow_outgoing_presence = false`
4. Optional: `allow_local_presence = false` (deaktiviert auch UI-Indikatoren)
5. `log = "warn"`
6. Reverse Proxy (Nginx/Caddy) fuer TLS — keine direkten Client-IPs im Tuwunel-Log

### Wenn Windows-Dev → Dendrite (Fallback)
1. `metrics.enabled: false`
2. `presence.enable_inbound/outbound: false` (teilweise)
3. `log_level: warn`
4. `real_ip_header: ""`
5. Nicht für Production mit echten User-Daten nutzen

### Beide Server
- Keine E-Mail-Registrierung aktivieren
- `allow_guest_registration = false`
- Token-basierte Registrierung
- Regelmäßige Updates (Matrix-Sicherheitslücken werden aktiv gefunden)

---

## Noch nicht gelöst / Offene Punkte

| Problem | Status | Workaround |
|---|---|---|
| Typing Notifications serverseitig deaktivieren | Keine Config in beiden Servern | Clients können individuell deaktivieren |
| Tuwunel IP-Logging Details | Wenig Dokumentation | Reverse Proxy mit IP-Stripping |
| Push Notification Metadata | Sygnal erhält Metadaten | UnifiedPush + eigener Sygnal-Server |
| Message Retention Dendrite | Nicht implementiert | Nur Tuwunel nutzen |

---

## Quellen
- [Tuwunel Konfiguration](https://tuwunel.chat/configuration.html)
- [Dendrite Konfiguration](https://matrix-org.github.io/dendrite/administration/configuration)
- [Dendrite Issue #3284 — Read Receipts](https://github.com/matrix-org/dendrite/issues/3284)
- [Dendrite Issue #3330 — Message Retention](https://github.com/matrix-org/dendrite/issues/3330)
- [Matrix Federation Privacy](https://matrix.org/blog/2019/11/09/avoiding-unwelcome-visitors-on-private-matrix-servers/)
