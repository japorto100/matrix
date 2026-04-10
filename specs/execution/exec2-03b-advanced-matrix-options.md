# exec2-03b: Advanced Matrix Options (Server-Auswahl, Onboarding, BYOS)

**Datum:** 10.04.2026
**Status:** Geplant (Backlog)
**Abhaengig von:** exec2-01 (Matrix Chat Core), exec-merge-chat (Hauptprojekt-Integration)
**Kontext:** Matrix ist unsichtbare Infrastruktur fuer Chat + Agents, kein eigenstaendiger Client.

---

## Architektur-Entscheidung: Account-Provisioning

### Default: Auto-Create auf eigenem Server (empfohlen)

```
User registriert sich bei tradeview-fusion
  → App erstellt automatisch Matrix-Account auf unserem Tuwunel
  → User sieht "Matrix" nie — ist unsichtbare Infrastruktur
  → Agents (@agent-*) sind lokal, keine Federation noetig
  → E2EE Keys werden automatisch gemanaged
```

**Warum:**
- Minimale Onboarding-Friction (User will traden, nicht Matrix konfigurieren)
- Agents leben lokal → schnellste Kommunikation, kein Federation-Overhead
- Volle Kontrolle ueber Message Retention, Compliance, Key Management
- Standard-Pattern fuer Apps die Matrix als Infrastruktur nutzen (Beeper, Element Call)

**Implementierung:** OIDC/MAS (Matrix Authentication Service)
- User loggt sich in tradeview-fusion ein (unsere Auth)
- MAS provisioniert Matrix-Session automatisch (delegated auth)
- Kein separater Matrix-Login noetig
- Token-Refresh transparent im Hintergrund

### Advanced Option: BYOS (Bring Your Own Server)

```
User → Settings → Advanced → "Eigenen Matrix-Server verwenden"
  → Homeserver URL eingeben (z.B. matrix.org, eigener Server)
  → Login/Registrierung auf externem Server
  → Federation: User joint Raeume auf unserem Server
  → Agents erreichbar via Federation (mit Einschraenkungen)
```

**Wann relevant:**
- Power-User mit bestehendem Matrix-Account
- Datenschutz-bewusste User die eigenen Server betreiben
- Enterprise mit eigenem Homeserver

**Einschraenkungen bei BYOS:**
- Federation-Latenz (Messages gehen ueber 2 Server)
- E2EE Key-Austausch komplexer (Cross-Server Verification)
- Nicht alle Features garantiert (Live-Location, Voice via LiveKit)
- Agent-Interaktion ueber Federation getestet sein muss

---

## Onboarding UI

### Phase 1: Registrierung/Login (Hauptprojekt)

```
┌─────────────────────────────────────────┐
│  tradeview-fusion                       │
│                                         │
│  [Email]     ___________________        │
│  [Passwort]  ___________________        │
│                                         │
│  [Registrieren]  [Login]                │
│                                         │
│  ─── oder ───                           │
│  [Google]  [GitHub]  [Apple]            │
│                                         │
│  (i) Matrix-Chat wird automatisch       │
│      eingerichtet.                      │
│      Eigenen Server? → Erweitert        │
└─────────────────────────────────────────┘
```

### Phase 2: Post-Login Setup (einmalig)

```
┌─────────────────────────────────────────┐
│  Willkommen! Dein Setup:               │
│                                         │
│  ✅ Account erstellt                    │
│  ✅ Matrix-Chat bereit                  │
│  ✅ Trading-Agent verfuegbar            │
│                                         │
│  Optionen:                              │
│  ○ Standard (empfohlen)                 │
│    Unser Server, alles automatisch      │
│                                         │
│  ○ Eigener Matrix-Server (erweitert)    │
│    Homeserver URL: _______________      │
│    ⚠ Federation noetig, nicht alle     │
│      Features garantiert                │
│                                         │
│  [Weiter]                               │
└─────────────────────────────────────────┘
```

### Phase 3: E2EE Key Setup (bei BYOS oder manuellem Setup)

```
┌─────────────────────────────────────────┐
│  Verschluesselung einrichten            │
│                                         │
│  ○ Automatisch (empfohlen)              │
│    Cross-Signing Keys werden generiert  │
│    Key Backup auf unserem Server        │
│                                         │
│  ○ Bestehende Keys importieren          │
│    Security Key eingeben: ________      │
│    oder Key-Datei hochladen [Browse]    │
│                                         │
│  ○ Neuen Key generieren                 │
│    ⚠ Alte Nachrichten nicht lesbar     │
│                                         │
│  [Einrichten]                           │
└─────────────────────────────────────────┘
```

---

## Settings (nach Onboarding)

### Matrix Settings in control-ui (User Mode)

```
control-ui → Settings Tab:

Matrix Chat
  Server: tuwunel.tradeview.local (Standard)  [Aendern]
  Account: @user123:tuwunel.tradeview.local
  Status: Verbunden ✅

Verschluesselung
  Cross-Signing: Verifiziert ✅
  Key Backup: Aktiv (letzte Sicherung: vor 2h)
  [Security Key anzeigen]  [Key Backup exportieren]
  [Neuen Key generieren]   [Geraet verifizieren]

Erweitert
  Sliding Sync URL: https://tuwunel.tradeview.local/sync
  [Anderen Server verbinden]  ← BYOS Flow
```

---

## Implementierung

### Phase A: Auto-Create (Minimum Viable)

- [ ] **A1:** OIDC/MAS Integration
  - tradeview-fusion Auth → MAS → Tuwunel Account Provisioning
  - Oder: Appservice Admin API fuer Account-Erstellung (einfacher, weniger OIDC-Abhaengigkeit)
  - Token wird im Frontend-Session gespeichert

- [ ] **A2:** Post-Login Matrix Init
  - Nach Login: `initMatrixClient()` mit auto-provisioniertem Token
  - Cross-Signing Bootstrap automatisch (wie in Go Appservice)
  - Key Backup automatisch aktiviert

- [ ] **A3:** Onboarding Wizard (optional)
  - Nur bei Erstanmeldung
  - Zeigt "Chat bereit" Status
  - Skip-Button fuer erfahrene User

### Phase B: BYOS (Advanced)

- [ ] **B1:** Server-Auswahl UI
  - Homeserver URL Input + Well-Known Discovery
  - Server-Capabilities pruefen (Sliding Sync, E2EE, etc.)
  - Warnung bei fehlenden Features

- [ ] **B2:** Federation Verify
  - Externer User joint Raeume auf unserem Server
  - Agent-Interaktion ueber Federation testen
  - E2EE Cross-Server Verification

- [ ] **B3:** E2EE Key Management UI
  - Security Key anzeigen/exportieren
  - Key Backup import/export
  - Cross-Signing Verification Flow (QR + SAS)
  - Neuen Key generieren (mit Warnung)

### Phase C: Multi-Account (spaeter)

- [ ] **C1:** Mehrere Matrix-Accounts gleichzeitig
  - Primaer: eigener Server (Standard)
  - Sekundaer: externer Server (BYOS)
  - Account-Switcher in Matrix Chat UI

---

## Verify-Gates

### Gate A: Auto-Create
- [ ] Neuer tradeview-fusion User → Matrix-Account automatisch erstellt
- [ ] Kein separater Matrix-Login noetig
- [ ] Cross-Signing + Key Backup automatisch
- [ ] Agent-Chat sofort funktionsfaehig nach Registrierung

### Gate B: BYOS
- [ ] Externer Homeserver (matrix.org) verbindbar
- [ ] Federation: externer User sieht Raeume auf unserem Server
- [ ] Agent-Interaktion ueber Federation funktioniert
- [ ] E2EE Cross-Server: Nachrichten lesbar

### Gate C: Key Management UI
- [ ] Security Key anzeigbar + exportierbar
- [ ] Key Backup import funktioniert
- [ ] Cross-Signing QR + SAS Verification
- [ ] Key-Generierung mit Warnung

---

## Risiken

| Risiko | Mitigation |
|---|---|
| OIDC/MAS nicht reif genug fuer Tuwunel | Fallback: Appservice Admin API fuer Account-Erstellung |
| Federation-Latenz bei BYOS | Klar kommunizieren: "Standard empfohlen, Federation = langsamere Experience" |
| E2EE Key-Verlust | Automatisches Key Backup, Security Key im Onboarding prominent zeigen |
| Multi-Account Komplexitaet | Phase C nur bei echtem Bedarf, nicht voreilig |

---

## Abhaengigkeiten

- exec2-01: Matrix Chat Core (Basis-Features)
- exec-05: NATS + E2EE Pipeline (Cross-Signing, Key Backup)
- exec-merge-chat: Hauptprojekt-Integration (Onboarding-Flow dort)
- exec-blocking C2: OIDC/MAS (Tuwunel Support noetig)
- Tuwunel: Well-Known Discovery, MAS Support, Federation Config
