# exec-05: NATS E2EE Pipeline — Go Appservice als Crypto-Gateway

**Datum:** 26.03.2026
**Status:** Geplant

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

- [ ] **A1:** Python Bridge — NATS Subscriber implementieren
  - `nats_url` Config ist vorhanden, Client-Code fehlt
  - Subscribe auf `matrix.message.>` (oder spezifischeres Subject)
  - Eingehende NATS-Message parsen → Agent Service aufrufen
  - Antwort zurück auf NATS Reply-Subject publishen

- [ ] **A2:** Go Appservice — NATS Reply-Handler
  - `SubscribeReplies` Code existiert (`natsbridge/bridge.go`)
  - Reply von Python empfangen → als Matrix-Nachricht senden (via Agent-Intent)
  - Prüfen ob der Agent-User im Raum ist, ggf. joinen

- [ ] **A3:** Python Bridge — matrix-nio Sync entfernen
  - Matrix-Client-Login und Sync-Loop rauswerfen
  - Nur noch NATS + HTTP Agent bleiben
  - `/health` Endpoint beibehalten

- [ ] **A4:** End-to-End Test
  - User sendet Nachricht in unverschlüsseltem Raum
  - Go Appservice → NATS → Python Bridge → LLM Mock → NATS → Go → Matrix
  - Antwort erscheint im Chat

### Phase B: E2EE aktivieren

- [ ] **B1:** Go Appservice — `MATRIX_E2EE_ENABLED=true` setzen
  - OlmMachine initialisiert sich, Device-Keys werden hochgeladen
  - `handleEncrypted()` in `server.go` entschlüsselt Events
  - Cross-Signing Seeds generieren + hochladen

- [ ] **B2:** Verschlüsselten Raum testen
  - User sendet in E2EE-Raum → Go entschlüsselt → NATS → Python → LLM Mock → Antwort
  - Antwort kommt verschlüsselt zurück beim User an

- [ ] **B3:** Cross-Signing für Bot
  - Bot-Device cross-signen (Admin-API oder manuell)
  - Browser verifiziert Bot → grünes Shield

- [ ] **B4:** Key Backup
  - `MATRIX_KEY_BACKUP_PASSWORD` setzen
  - Megolm-Keys werden bei Stop exportiert, bei Start importiert
  - Frisches Deployment mit vorhandenem Backup → alte Nachrichten lesbar

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

### Nach exec-05 zu ändern
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

## Abhängigkeiten

- Go Appservice muss korrekt als Appservice bei Tuwunel registriert sein (registration.yaml)
- NATS JetStream muss laufen
- LLM Mock oder echter Agent Service muss auf :8094 erreichbar sein
- Für Phase B: libolm/goolm muss im Go Build funktionieren (`-tags goolm`)
