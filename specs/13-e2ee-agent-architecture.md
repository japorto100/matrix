# E2EE Agent Architecture — Ist-Zustand

## Übersicht

Dieses Dokument beschreibt den aktuellen Zustand der Verschlüsselungs- und Nachrichtenfluss-Architektur
zwischen User, Homeserver, Go Appservice, Python Agent Bridge und LLM.

---

## Nachrichtenfluss (Ist-Zustand)

```
┌──────────┐      ┌───────────┐      ┌────────────────┐      ┌──────────────┐      ┌───────────┐
│  Browser  │─────►│  Tuwunel  │─────►│ Python Bridge  │─────►│  LLM Mock /  │─────►│  Antwort  │
│ (Next.js) │ E2EE │(Homeserver)│Sync │ (matrix-nio)   │ HTTP │  Agent Svc   │      │  zurück   │
└──────────┘      └───────────┘      └────────────────┘      └──────────────┘      └───────────┘
                                            │
                                     ┌──────┴──────┐
                                     │ Go Appservice│  ← Empfängt Events, aber leitet
                                     │ (mautrix-go) │     NICHT an Python weiter (NATS
                                     └─────────────┘     nicht connected)
                                            │
                                     ┌──────┴──────┐
                                     │    NATS     │  ← Läuft, aber wird von Python
                                     │  (JetStream)│     Bridge NICHT genutzt
                                     └─────────────┘
```

---

## Komponenten-Status

### Browser (Next.js Chat)
- Eingeloggt als `@alice:matrix.local` mit Device `ALICE01`
- matrix-js-sdk mit Rust Crypto (WASM) für E2EE
- Verschlüsselt/entschlüsselt Nachrichten client-seitig
- Cross-Signing: Gerät nicht verifiziert (gelbes Shield)

### Tuwunel (Homeserver)
- `encryption_enabled_by_default_for_room_type = "invite"` → Invite-Räume automatisch verschlüsselt
- Speichert verschlüsselte Events (kann nicht mitlesen)
- STUN-Server konfiguriert (Cloudflare + Google)

### Go Appservice
- Läuft auf :8090, verbunden mit Tuwunel via Appservice-Protokoll
- `MATRIX_E2EE_ENABLED=false` → empfängt verschlüsselte Events aber kann sie nicht lesen
- Bot-User: `@appservice-bot:matrix.local`
- Agent-Namespace: `@agent-*:matrix.local`
- NATS-Publisher: Code vorhanden (`natsbridge.PublishInbound`), aber Python Bridge subscribed nicht
- Crypto-Code: OlmMachine vorhanden, aber deaktiviert

### Python Agent Bridge
- Läuft auf :8097 als eigenständiger Matrix-Client (matrix-nio)
- Bot-User: Eingeloggt mit eigenem Account (NICHT als Appservice-Ghost)
- Empfängt Events direkt via Matrix Sync (NICHT via NATS)
- `nats_url` in Config vorhanden aber **nicht genutzt**
- Filterung:
  - Eigene Nachrichten ignoriert
  - Homeserver-Whitelist (`matrix.local`)
  - Mention-Only in Gruppenchats (>2 User)
- Leitet Nachrichtentext per HTTP an LLM Mock/Agent Service weiter
- Kann verschlüsselte Räume **nicht lesen** (kein E2EE Support in matrix-nio ohne libolm)

### LLM Mock Agent
- Läuft auf :8094
- Einfacher HTTP-Service mit SSE-Streaming
- Empfängt Klartext, antwortet mit Mock-Antworten
- Kein Matrix-Wissen, kein E2EE

### NATS
- Läuft auf :4222 mit JetStream
- Go Appservice published Events → aber niemand subscribed
- Effektiv ungenutzt im aktuellen Flow

---

## E2EE-Status pro Raum

| Raum | Verschlüsselt | Grund |
|---|---|---|
| Empty room (1) | ✅ Ja | Invite-Raum, Tuwunel-Default |
| Empty room (2) | ✅ Ja | Invite-Raum, Tuwunel-Default |
| test | ✅ Ja | Invite-Raum, Tuwunel-Default |
| General | ❌ Nein | Public/Join-Raum |
| matrix.local Admin Room | ❌ Nein | Admin-Raum |

---

## Probleme im Ist-Zustand

### 1. NATS ist Infrastruktur-Overhead ohne Nutzen
NATS läuft, Go Appservice published, aber Python Bridge subscribed nicht.
Der gesamte NATS-Pfad ist toter Code.

### 2. Python Bridge kann E2EE-Räume nicht bedienen
matrix-nio ohne `[e2e]` Extra kann nicht entschlüsseln.
In verschlüsselten Räumen (die Tuwunel automatisch erstellt) funktioniert der Bot nicht.

### 3. Doppelte Matrix-Verbindungen
Go Appservice UND Python Bridge sind beide als Matrix-Clients verbunden.
Beide empfangen dieselben Events. Redundant.

### 4. Keine Agent-Isolation
Wenn E2EE im Go Appservice aktiviert wird, entschlüsselt EIN Bot ALLES.
Alle Agents teilen denselben NATS-Kanal — keine Isolation.

### 5. Cross-Signing nicht abgeschlossen
Browser-Device nicht verifiziert → andere E2EE-Clients vertrauen unseren Keys nicht.
Bot-Device ebenfalls nicht cross-signed.

---

## Konfiguration

### Go Appservice (.env.development)
```
MATRIX_E2EE_ENABLED=false
MATRIX_CRYPTO_DB_PATH=./data/crypto.sqlite3
MATRIX_BOT_USER_ID=@appservice-bot:matrix.local
MATRIX_AGENT_PREFIX=agent-
NATS_URL=nats://127.0.0.1:4222
```

### Python Bridge (.env)
```
BOT_USER_ID=@appservice-bot:matrix.local  (oder eigener Bot-Account)
AGENT_SERVICE_URL=http://127.0.0.1:8094
NATS_URL=nats://127.0.0.1:4222  (konfiguriert aber ungenutzt)
MENTION_ONLY_IN_GROUPS=true
ALLOWED_HOMESERVERS=matrix.local
```

### Tuwunel (tuwunel.toml)
```toml
encryption_enabled_by_default_for_room_type = "invite"
turn_uris = ["stun:stun.cloudflare.com:3478", "stun:stun.l.google.com:19302"]
```
