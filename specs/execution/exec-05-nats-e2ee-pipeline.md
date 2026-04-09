# exec-05: NATS E2EE Pipeline — Go Appservice als Crypto-Gateway

**Datum:** 26.03.2026 (Review 30.03.2026, Implementation 30.03.2026)
**Status:** Phase A+B implementiert — E2E-Test (A4) ausstehend

---

## Warum

### Problem
Die Python Agent Bridge ist aktuell ein eigenständiger Matrix-Client (matrix-nio) der
Events direkt via Sync empfängt. Das hat drei Probleme:

1. **E2EE-Räume funktionieren nicht** — matrix-nio ohne libolm kann nicht entschlüsseln.
   Tuwunel erstellt Invite-Räume automatisch verschlüsselt → Bot kann dort nicht mitlesen.

2. **NATS ist toter Code** — Go Appservice published auf NATS, Python subscribed nicht.
   Redundante Infrastruktur ohne Nutzen.

3. **Doppelte Verbindungen** — Sowohl Go als auch Python verbinden sich mit Tuwunel.
   Doppelter Sync-Traffic, doppelte Session-Verwaltung.

### Ist-Zustand (aktueller Flow)
```
Ist:
User → Tuwunel → Python Bridge (matrix-nio Sync, eigener Login) → LLM Mock (HTTP :8094)
                                                                     ↓
User ← Tuwunel ← Python Bridge (sendet direkt via matrix-nio)  ← LLM Antwort

Go Appservice → empfängt Events → published auf NATS → niemand subscribed (toter Code)
```

- Python Bridge = eigenständiger Matrix-Client mit eigenem Login + Sync-Session
- 2 Matrix-Verbindungen zu Tuwunel (Go + Python)
- E2EE nicht möglich (matrix-nio ohne libolm kann nicht entschlüsseln)
- NATS läuft aber wird von Python nicht genutzt
- Bot funktioniert nur in unverschlüsselten Räumen

### Soll-Zustand
Go Appservice wird zum **einzigen Matrix-Gateway**:
- Empfängt Events via Appservice-Protokoll (kein Sync nötig)
- Entschlüsselt E2EE-Nachrichten (OlmMachine, bereits implementiert)
- Publiziert Klartext auf NATS (Subject pro Raum oder Agent)
- Python Bridge wird zum reinen NATS-Consumer + HTTP-Agent-Client
- Python Bridge braucht kein matrix-nio, kein E2EE, keine Matrix-Session

```
Soll:
User → Tuwunel → Go Appservice (entschlüsselt) → NATS → Python Bridge → LLM
                                                   NATS ← Python Bridge ← LLM
                  Go Appservice (verschlüsselt) ← NATS
User ← Tuwunel ← Go Appservice
```

### Vorteile
- **E2EE funktioniert** — Go entschlüsselt, Python bekommt Klartext
- **Saubere Trennung** — Go = Matrix/Crypto, Python = Business-Logik/LLM
- **Skalierbar** — Mehrere Python-Agents können verschiedene NATS-Subjects subscriben
- **Isolation möglich** — NATS-Subjects per Raum oder Agent partitionierbar
- **Ein Matrix-Endpunkt** — Nur Go verbindet sich mit Tuwunel

---

## Schritte

### Phase A: NATS-Pfad aktivieren

- [x] **A1:** Python Bridge — NATS Subscriber implementieren ✅ (30.03.2026)
  - `bridge/nats_handler.py` erstellt — NATSHandler Klasse
  - Subscribe auf `matrix.message.inbound`, Agent-Call via HTTP SSE, Reply auf `matrix.message.reply`
  - Reconnect-Handling, Graceful Drain, Error-Logging
  - `bridge/app.py` — Lifespan: NATS-Handler statt MatrixBotClient
  - `bridge/config.py` — Vereinfacht: nur NATS + Agent + Service Config, `agent_user_id` neu

- [x] **A2:** Go Appservice — NATS Publisher + Reply-Handler ✅
  - `PublishInbound()` auf `matrix.message.inbound` implementiert (`natsbridge/bridge.go:63-78`)
  - `SubscribeReplies()` auf `matrix.message.reply` implementiert (`natsbridge/bridge.go:80-95`)
  - `handleAgentReply()` Callback in `server.go:391-424`
  - Reply von Python empfangen → als Matrix-Nachricht senden (via Agent-Intent)
  - Auto-Join für Agent-User bei Invite (`handleMembership()`)

- [x] **A3:** Python Bridge — matrix-nio Sync entfernen ✅ (30.03.2026)
  - `bridge/matrix_client.py` geloescht
  - `matrix-nio` aus `pyproject.toml` entfernt, `uv sync` clean
  - Imports korrigiert: `agent_bridge.` → `bridge.`
  - `/health` Endpoint zeigt jetzt NATS-Status statt Matrix-Bot-Status
  - Python Bridge ist jetzt reiner NATS-Consumer + HTTP-Agent-Client

- [x] **A3b:** Go Appservice — Message-Filter vor NATS-Publish ✅ (30.03.2026)
  - `shouldForwardToAgent()` in `server.go` — DMs (≤2 Member) immer, Gruppen nur bei:
    - `@agent-*` Mention im Body
    - Reply auf eine Nachricht (RelatesTo InReplyTo)
    - Trigger-Woerter: "agent,", "hey agent", "bot,", "hey bot"
  - `roomMembers` Map im Server-Struct (unabhaengig von E2EE)
  - `MentionOnlyInGroups` Config (ENV `MENTION_ONLY_IN_GROUPS`, default `true`)
  - golangci-lint: 0 Issues (+ 9 pre-existing errcheck in anderen Dateien mitgefixt)

- [ ] **A4:** End-to-End Test
  - User sendet Nachricht in unverschlüsseltem Raum
  - Go Appservice → NATS → Python Bridge → LLM Mock → NATS → Go → Matrix
  - Antwort erscheint im Chat

### Phase B: E2EE aktivieren

- [x] **B1:** Go Appservice — E2EE Code implementiert ✅
  - OlmMachine mit goolm (Pure-Go, kein CGO) (`crypto/machine.go`)
  - `handleEncrypted()` in `server.go:276-297` entschlüsselt Events
  - SQLite Crypto-Store (`modernc.org/sqlite`, kein CGO)

- [x] **B2:** E2EE im Dev-Stack aktiviert ✅ (30.03.2026)
  - `MATRIX_E2EE_ENABLED=true` in `.env.development` gesetzt
  - ⚠️ Manueller E2E-Test steht noch aus (A4)

- [x] **B3:** Cross-Signing für Bot ✅
  - `ensureCrossSigning()` implementiert (`machine.go:111-178`)
  - MSK/SSK/USK generiert, Seeds persistiert in `cross_signing_seeds.json`
  - MSC4153-kompatibel (IdentityBasedStrategy für Element X)

- [x] **B4:** Key Backup ✅
  - `ExportKeyBackup()` implementiert (`machine.go:180-206`)
  - `importKeyBackup()` bei Start (`machine.go:208-229`)
  - Pfad: `<dbDir>/megolm_keys_backup.bin`, Passphrase-verschlüsselt
  - `MATRIX_KEY_BACKUP_PASSWORD` konfigurierbar

### Phase C: Agent-Isolation (Optional)

- [ ] **C1:** NATS-Subjects per Raum partitionieren
  - Statt `matrix.message.*` → `matrix.message.{roomId}`
  - Python Bridge subscribed nur auf Räume die ihr Agent bedient

- [ ] **C2:** Agent-Routing im Go Appservice
  - Nachricht an `@agent-trading:matrix.local` → NATS Subject `matrix.message.trading`
  - Nachricht an `@agent-research:matrix.local` → NATS Subject `matrix.message.research`
  - Verschiedene Python-Instanzen können verschiedene Agents bedienen

- [ ] **C3:** Access Control auf NATS
  - NATS Authorization: Python-Trading darf nur `matrix.message.trading` lesen
  - Verhindert dass ein Agent-Service andere Agents' Nachrichten sieht

- [x] **C4:** Agent Thread-Support ✅ (Thread Root wird via NATS weitergereicht)
  - Agent wird im Thread mentioned → Go Appservice erkennt Thread-Kontext
  - NATS-Message enthaelt threadRootId → Python Agent antwortet im Thread (nicht Hauptchat)
  - Go Appservice nutzt `client.sendMessage(roomId, threadId, content)` fuer Thread-Reply
  - Agent-Thread-Strategie: kurze Antwort → Hauptchat, lange Analyse → Thread erstellen

---

## Risiken

| Risiko | Mitigation |
|---|---|
| NATS-Latenz | NATS ist In-Memory, Latenz <1ms lokal |
| NATS Down | Go Appservice queued Messages (JetStream) |
| OlmMachine Bugs | Mautrix-go Crypto ist battle-tested (Bridges nutzen es) |
| Key-Verlust | Key Backup File + SQLite Crypto-Store |
| Klartext auf NATS | NATS läuft lokal, kein externer Zugriff. Für Prod: NATS TLS |

---

## E2EE-Entscheidungen (aus exec-04 UI-Rework)

### Aktueller Zustand (vor exec-05)
- Tuwunel: `encryption_enabled_by_default_for_room_type = "off"` — Server verschlüsselt nichts automatisch
- DMs: Immer unverschlüsselt (LLM Mock / Python Bridge können nicht entschlüsseln)
- CreateRoomDialog: "Privater Raum" = invite + E2EE, "Offener Raum" = public + kein E2EE
- Header: Lock-Icon grün (verschlüsselt) / rot (nicht verschlüsselt), kein gelbes Shield

### Nach exec-05 geaendert (30.03.2026)
- [x] **E2EE Blacklist**: `NEXT_PUBLIC_E2EE_BLACKLIST_UNVERIFIED` ENV eingefuehrt
  - Dev (`.env.local`): `false` — Keys an alle Devices (Bot muss nicht verified sein)
  - Prod (`.env.production`): `true` — Keys nur an cross-signed Devices (MSC4153)
  - Go Bot muss einmal laufen + Cross-Signing Keys hochladen bevor Prod-Blacklist aktiv
- [x] **Go `.env.production`**: `MENTION_ONLY_IN_GROUPS` + `AGENT_SERVICE_URL` + `MEMORY_SERVICE_URL` ergaenzt
- [ ] **User↔User DMs**: Optional E2EE an (Checkbox im CreateDMDialog, default aus)
- [ ] **Agent-DMs**: Dev = unverschlüsselt (einfacher), Prod = E2EE empfohlen
  - Dev: Go liest Klartext direkt, kein OlmMachine nötig
  - Prod: E2EE schützt ruhende Daten (DB-Leak, Backup-Leak, Netzwerk-Sniffer)
  - Go Appservice joined Agent-Räume → bekommt Megolm Keys → kann entschlüsseln
  - User↔User DMs: Go ist NICHT Member → kann NICHT entschlüsseln (sicher by design)
- [ ] **Tuwunel default bleibt `"off"`**: Clients entscheiden pro Raum
- [ ] **Cross-Signing**: Nur relevant wenn User↔User E2EE aktiviert wird
- [ ] **Sicherheitsregel**: Agent-Namespace (`@agent-*`) joined nur Agent-Räume (Appservice-Regex), NICHT User↔User DMs

---

## E2EE Sicherheitsmodell — Go Gateway + E2BE (28.03.2026)

### Warum E2EE + Go Gateway sicherer ist als non-E2EE

```
Non-E2EE:   User → Klartext → Tuwunel (DB hat Klartext) → Go Appservice → Agent
E2EE + GW:  User → Ciphertext → Tuwunel (DB hat NUR Ciphertext) → Go (entschluesselt im RAM) → Agent
```

Bei E2EE sieht der Homeserver nie den Klartext. DB-Leak, Backup-Leak, Netzwerk-Sniffer — alles geschuetzt.
Nur der Go Appservice (selbst betrieben) sieht Klartext — und nur im RAM, nicht persistent.

### Standard-Pattern — kein Sonderweg

Alle Matrix Bridges (mautrix WhatsApp/Telegram/Signal/Discord) nutzen dasselbe Pattern.
mautrix nennt es **E2BE (End-to-Bridge Encryption)**: Bridge entschluesselt E2EE, verarbeitet, antwortet verschluesselt.
Klare Aussage von mautrix: "End-to-bridge encryption ≠ end-to-end encryption. Trust your bridge operator."
Da wir den Bot selbst betreiben → Trust gegeben.

### Key Deletion — Forward Secrecy (zu evaluieren)

**Ohne Key Deletion (aktueller Plan):**
- Go Appservice entschluesselt Nachricht
- Megolm Session Key bleibt im Crypto-Store
- Server-Hack spaeter → alte Nachrichten entschluesselbar

**Mit Key Deletion (E2BE Best Practice):**
- Go Appservice entschluesselt Nachricht
- Megolm Session Key wird SOFORT geloescht
- Server-Hack spaeter → Keys weg → alte Nachrichten geschuetzt

**Evaluation noetig fuer Agent:**
- Agent braucht History-Kontext um sinnvoll zu antworten
- Sofortiges Key-Loeschen = Agent kann nach Neustart keine History lesen
- Option: Keys X Stunden behalten statt sofort loeschen (Kompromiss)
- Option: Agent-relevanten Kontext in eigenem Store speichern (nicht Megolm Keys)
- [ ] **TODO:** Key Deletion Strategie fuer Agent evaluieren (Config-Flag `MATRIX_DELETE_KEYS_AFTER_DECRYPT`)

### Agent vs Bridges — getrennte Crypto-Stores

| | Agent (Go Appservice) | Bridges (E2BE fuer WhatsApp/Telegram) |
|---|---|---|
| **Key Deletion** | Aus oder verzoegert — Agent braucht Kontext | An — Bridge leitet nur live weiter |
| **Crypto-Store** | Eigener SQLite Store, Keys bleiben (laenger) | Eigener SQLite Store, Keys sofort loeschen |
| **Bot-User-IDs** | `@agent-*:domain` | `@whatsapp-*:domain`, `@telegram-*:domain` |
| **Appservice Reg** | Separate registration.yaml | Separate registration.yaml pro Bridge |
| **Prozess** | Go Appservice | mautrix Bridge (Python/Go) |

Separate Prozesse, separate Registrierungen, separate Crypto-Stores — kein Konflikt.

### E2BE fuer andere Channels

Ausgelagert nach **exec-05b-messaging-bridges.md**:
- mautrix-whatsapp, mautrix-signal (P1)
- mautrix-telegram, mautrix-meta (P2)
- mautrix-discord (P3)
- Alle nutzen dasselbe E2BE Crypto-Pattern, eigener Prozess + Crypto-Store pro Bridge

---

## Seit exec-05 hinzugekommene Realitäten (30.03.2026)

### Go Gateway ist jetzt mehr als NATS-Bridge
- Go Appservice ist SSE-Proxy für Agent-Chat (`/api/v1/agent/chat` → Python 8094)
- Audio STT/TTS Proxy, Memory Service Proxy, Agent Tools Proxy — alles über HTTP
- Agent-Chat-UI (19 Komponenten) spricht direkt via BFF → Go → Python (kein NATS-Pfad)
- NATS ist nur für den Matrix-Event-Pfad relevant, nicht für Agent-Chat-UI

### DevStack
- `scripts/devstack2.ps1` ist der aktuelle Dev-Stack (nicht docker-compose)
- docker-compose.yml ist veraltet (zeigt auf `./python-agent-bridge`, existiert nicht mehr)

### vodozemac-python existiert (v0.9.0, Juli 2025)
- Python Bindings für vodozemac: `matrix-nio/vodozemac-python` auf GitHub
- Prebuilt wheels für Python 3.14
- matrix-nio selbst nutzt noch python-olm (libolm) für E2EE — Migration zu vodozemac unklar
- Soatok Feb 2026: Crypto-Issues in vodozemac gemeldet (Matrix: "nicht praktisch exploitbar")

---

## Architektur-Entscheidung: E2EE bei Multi-Agent Skalierung (OFFEN)

### Kontext
Bei 1000 Usern mit jeweils eigenen Agents: Soll Go zentral entschlüsseln (E2BE)
oder jeder Agent seine eigene E2EE-Identität haben?

### Option A: Zentrales Go Gateway (aktueller Plan)
```
1000 User → Tuwunel → 1 Go Appservice (entschlüsselt ALLE) → NATS → N Agent-Harnesses
```
- **Pro:** Ein Crypto-Store, ein Device, Standard E2BE (wie alle mautrix Bridges)
- **Contra:** Single Point of Trust, alle Agents sehen theoretisch alles über NATS

### Option B: Per-Agent E2EE (matrix-nio + vodozemac pro Agent)
```
1000 User → Tuwunel → Go (Routing) → Agent-Harness (eigenes E2EE, eigener Crypto-Store)
```
- **Pro:** Isolation (kompromittierter Agent = nur dessen Räume), horizontal skalierbar
- **Contra:** N Devices, N Cross-Signing Setups, matrix-nio E2EE fragil

### Option C: Hybrid (empfohlen zur Evaluation)
```
User → Tuwunel → Go (Routing + Fallback-Decrypt)
                     ↓
          NATS (Ciphertext ODER Klartext je nach Agent-Capability)
                     ↓
          Agent-Harness (eigenes E2EE ODER reiner NATS-Consumer)
```
- Einfache Agents: Go entschlüsselt, Agent bekommt Klartext
- Privilegierte Agents: Eigener Matrix-Client mit vodozemac

### Option D: Web-Client Keys an Agent weitergeben
- MSC4268 (Successor zu MSC3061): Keys als verschlüsselter Blob bei Room-Invite
- `m.forwarded_room_key`: User-Client kann Megolm-Keys an verified Bot forwarden
- **Voraussetzung:** Bot-Device muss cross-signed verified sein
- **Risiko:** Forwarded Keys haben geringeren Trust-Level (UI zeigt Warnung)
- **Vorteil:** Kein eigener Sync nötig, Bot bekommt History-Keys
- **Status:** MSC4268 in Element Web + Element X implementiert

### NATS vs HTTP für Voice/Agent-Chat
- NATS: Gut für async Matrix-Events (fan-out, buffering, agent-routing)
- HTTP/SSE: Besser für synchrone Agent-Chat-Responses (Token-Streaming)
- Voice/Audio: LiveKit (WebRTC), nicht NATS — Sub-20ms Latenz nötig
- **Empfehlung:** NATS für Matrix-Events, HTTP für Agent-Chat, LiveKit für Voice

### TODO
- [ ] Architektur-Entscheidung A/B/C/D treffen
- [ ] vodozemac-python evaluieren (Reife, Kompatibilität mit matrix-nio)
- [ ] Key-Deletion-Strategie für Agents evaluieren (`MATRIX_DELETE_KEYS_AFTER_DECRYPT`)
- [ ] JetStream Persistence für `matrix.message.*` konfigurieren (Prod)
- [ ] NATS TLS für Prod

---

## Verify Gates

### Gate 1: NATS-Pfad funktioniert (Phase A)
- [ ] Python Bridge subscribed auf `matrix.message.inbound`
- [ ] Go Appservice empfängt Reply auf `matrix.message.reply`
- [ ] matrix-nio Sync-Loop entfernt (nur noch NATS)
- [ ] End-to-End: User → Matrix → Go → NATS → Python → LLM → NATS → Go → Matrix
- [ ] Keine doppelte Tuwunel-Verbindung mehr

### Gate 2: E2EE funktioniert (Phase B)
- [ ] `MATRIX_E2EE_ENABLED=true` im Dev-Stack aktiv
- [ ] Go entschlüsselt m.room.encrypted Events erfolgreich (Log-Check)
- [ ] Go verschlüsselt Antworten in E2EE-Räumen (MSC4381 Privacy)
- [ ] Cross-Signing: Bot-Device hat SSK-Signatur
- [ ] Element X / Next.js Client sendet Keys an Bot (MSC4153)
- [ ] Key Backup: Restart → alte Messages noch lesbar

### Gate 3: Agent-Isolation (Phase C)
- [ ] NATS-Subjects pro Agent partitioniert
- [ ] Agent-Routing im Go Appservice (Mention → Subject)
- [ ] NATS Authorization Rules (Agent darf nur eigenes Subject lesen)

### Gate 4: Crypto-Library Entscheidung
- [ ] goolm vs vodozemac evaluiert (PQXDH-Bedarf? CGO-Akzeptanz?)
- [ ] vodozemac-python getestet (falls Option B/C gewählt)
- [ ] Soatok Feb 2026 Issues bewertet (all-zero X25519, truncated MACs)

---

## Hinweis: Infra-/Eval-/Blocking-Sammlung

Einige Punkte dieses Slices sind absichtlich **infra-/umgebungsabhängig** oder **strategisch blockiert**
und werden gesammelt in:

- `exec-eval.md` (infra/umgebung/verify-runbooks, z.B. JetStream/TLS)
- `exec-blocking.md` (extern blockiert, z.B. Crypto-Library Entscheidung / Provider)

---

## Abhängigkeiten

- Go Appservice muss korrekt als Appservice bei Tuwunel registriert sein (registration.yaml)
- NATS JetStream muss laufen
- LLM Mock oder echter Agent Service muss auf :8094 erreichbar sein
- Für Phase B: goolm im Go Build (`-tags goolm`) — bereits funktional
- Für Option B/C: vodozemac-python oder matrix-rust-sdk-crypto Python Bindings
