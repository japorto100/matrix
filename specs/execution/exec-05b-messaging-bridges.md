# exec-05b: Messaging Bridges — WhatsApp, Signal, Telegram, Meta, Discord

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-05 (NATS E2EE Pipeline muss funktionieren)

---

## Warum

### Kontext
Nach exec-05 ist Go Appservice das einzige Matrix-Gateway mit E2BE.
Alle mautrix-Bridges nutzen dasselbe Pattern: eigener Prozess, eigene Appservice-Registration,
eigener Crypto-Store. Die Infrastruktur (Tuwunel, NATS, Go Gateway) ist bereits vorhanden.

### Ziel
User koennen ueber ihre bevorzugte Messaging-Plattform mit Matrix-Raeumen und Agents kommunizieren.
Nachrichten fliessen: WhatsApp/Signal/Telegram/etc. -> Bridge -> Matrix -> Go Appservice -> Agent.

### Architektur-Uebersicht

```
WhatsApp User ──> mautrix-whatsapp ──┐
Signal User   ──> mautrix-signal   ──┤
Telegram User ──> mautrix-telegram ──┼──> Tuwunel ──> Go Appservice ──> NATS ──> Agent
Instagram User ─> mautrix-meta    ──┤
Discord User  ──> mautrix-discord  ──┘

Jede Bridge = eigener Prozess, eigene registration.yaml, eigener Crypto-Store
```

---

## Bridges im Detail

### 1. mautrix-whatsapp (Prioritaet 1)

**Was:** Matrix <-> WhatsApp puppeting bridge (Go)
**Wie:** WhatsApp Web Multi-Device Linking (QR-Code), KEIN Business-API noetig
**E2BE:** Ja (eigener OlmMachine, eigener Crypto-Store)
**Namespace:** `@whatsapp-.*:matrix.local`
**Port:** 29318 (default)
**Status:** Production-ready, battle-tested, aktivste mautrix-Bridge

**Einschraenkungen:**
- Nutzt WhatsApp Web Protokoll (Reverse-Engineered, nicht offizielle API)
- Meta kann theoretisch brechen (selten, mautrix reagiert schnell)
- Ein WhatsApp-Account pro Bridge-User (nicht multi-tenant ohne Aufwand)
- DMA-Interoperabilitaet (Element arbeitet an offizieller WhatsApp<->Matrix API) koennte
  mautrix-whatsapp langfristig ersetzen — aber Stand 03/2026 noch nicht produktionsreif

### 2. mautrix-signal (Prioritaet 1)

**Was:** Matrix <-> Signal puppeting bridge (Go)
**Wie:** Signal Linked Device (wie Signal Desktop)
**E2BE:** Ja
**Namespace:** `@signal-.*:matrix.local`
**Port:** 29328 (default)
**Status:** Production-ready

**Einschraenkungen:**
- Signal erlaubt max. 5 Linked Devices pro Account
- Signal kann Linked-Device-Protokoll aendern (passiert selten)

### 3. mautrix-telegram (Prioritaet 2)

**Was:** Matrix <-> Telegram puppeting bridge (Go)
**Wie:** Telegram User-Login oder Bot-Token
**E2BE:** Ja
**Namespace:** `@telegram-.*:matrix.local`
**Port:** 29317 (default)
**Status:** Production-ready, Megabridge-Rewrite laeuft (Dez 2025)

**Besonderheit:**
- Kann mit Bot-Token im Generic-Relay-Modus laufen (kein persoenlicher Account noetig)
- Telegram Bots haben eigenes Oekosystem (Commands, Inline-Queries)

### 4. mautrix-meta (Prioritaet 2)

**Was:** Matrix <-> Facebook Messenger + Instagram DMs puppeting bridge (Go)
**Wie:** Facebook/Instagram Login
**E2BE:** Ja
**Namespace:** `@meta-.*:matrix.local` (oder `@facebook-.*` / `@instagram-.*`)
**Port:** 29319 (default)
**Status:** Production-ready, aktiv maintained (letztes Release Feb 2026)

**Besonderheit:**
- Ein Binary fuer Messenger + Instagram
- Encrypted Chats auf Instagram werden unterstuetzt (Placeholder-Support)

### 5. mautrix-discord (Prioritaet 3)

**Was:** Matrix <-> Discord puppeting bridge (Go)
**Wie:** Discord User-Token (Self-Bot) oder Bot-Token
**E2BE:** Ja
**Namespace:** `@discord-.*:matrix.local`
**Port:** 29334 (default)
**Status:** Stabil, Megabridge-Rewrite gestartet (Dez 2025)

**Besonderheit:**
- Discord Webhooks fuer Relay-Modus (unique feature)
- Room v12 Support seit Aug 2025

---

## Phasen

### Phase 1: WhatsApp + Signal (Prioritaet 1)

- [ ] **1.1:** mautrix-whatsapp aufsetzen
  - Docker Container oder Binary
  - registration.yaml generieren (`@whatsapp-.*:matrix.local`)
  - Tuwunel Appservice-Config ergaenzen
  - QR-Code Linking testen
- [ ] **1.2:** mautrix-signal aufsetzen
  - Docker Container oder Binary
  - registration.yaml generieren (`@signal-.*:matrix.local`)
  - Tuwunel Appservice-Config ergaenzen
  - Signal Linked Device testen
- [ ] **1.3:** E2BE fuer beide Bridges aktivieren
  - Eigener Crypto-Store pro Bridge (SQLite)
  - Cross-Signing Bootstrap pro Bridge
  - Verschluesselte Raeume testen
- [ ] **1.4:** Agent-Integration testen
  - WhatsApp User schreibt -> Bridge -> Matrix E2EE Raum -> Go entschluesselt -> NATS -> Agent
  - Agent antwortet -> NATS -> Go verschluesselt -> Matrix -> Bridge -> WhatsApp User
  - Dasselbe fuer Signal

### Phase 2: Telegram + Meta (Prioritaet 2)

- [ ] **2.1:** mautrix-telegram aufsetzen
  - Bot-Token Modus evaluieren (kein persoenlicher Account noetig)
  - registration.yaml generieren
- [ ] **2.2:** mautrix-meta aufsetzen
  - Facebook Messenger + Instagram DMs
  - registration.yaml generieren
- [ ] **2.3:** E2BE + Agent-Integration fuer beide testen

### Phase 3: Discord (Prioritaet 3)

- [ ] **3.1:** mautrix-discord aufsetzen
  - Bot-Token Modus (empfohlen)
  - Webhook Relay evaluieren
- [ ] **3.2:** E2BE + Agent-Integration testen

### Phase 4: DevStack Integration

- [ ] **4.1:** Alle Bridges in `devstack2.ps1` integrieren
  - Start/Stop/Health fuer jede Bridge
  - Env-Vars pro Bridge
- [ ] **4.2:** docker-compose.yml aktualisieren (falls Docker-Modus genutzt)
- [ ] **4.3:** Setup-Script fuer Bridge-Registrierungen bei Tuwunel

---

## Verify Gates

### Gate 1: WhatsApp + Signal funktioniert
- [ ] WhatsApp User sendet Nachricht -> erscheint in Matrix-Raum
- [ ] Signal User sendet Nachricht -> erscheint in Matrix-Raum
- [ ] Matrix User antwortet -> erscheint in WhatsApp/Signal
- [ ] E2BE: Bridge entschluesselt/verschluesselt korrekt (Log-Check)
- [ ] Agent antwortet auf WhatsApp/Signal-Nachricht via Matrix Pipeline

### Gate 2: Telegram + Meta funktioniert
- [ ] Telegram Bot empfaengt Messages -> Matrix -> Agent -> Antwort
- [ ] Instagram DM -> Matrix -> Agent -> Antwort
- [ ] Facebook Messenger -> Matrix -> Agent -> Antwort

### Gate 3: Discord funktioniert
- [ ] Discord Channel <-> Matrix Raum gebriddged
- [ ] Agent antwortet auf Discord-Nachrichten

### Gate 4: Alle Bridges E2BE-secure
- [ ] Jede Bridge hat eigenen Crypto-Store (kein Sharing mit Go Appservice)
- [ ] Cross-Signing pro Bridge verifiziert
- [ ] Key Backup pro Bridge konfiguriert
- [ ] Klartext nur im RAM der jeweiligen Bridge (nicht in Tuwunel DB)

---

## Risiken

| Risiko | Mitigation |
|---|---|
| WhatsApp Web Protokoll bricht | mautrix Team reagiert schnell (<48h historisch), DMA-API als Fallback-Pfad |
| Signal aendert Linked-Device API | Selten, mautrix-signal tracked Signal-Releases |
| Meta sperrt Account | Fuer Prod: Meta Business Verification erwaegen |
| Viele Prozesse (5 Bridges + Go + Python) | DevStack orchestriert, Health-Checks pro Service |
| Crypto-Store Corruption | Key Backup pro Bridge, SQLite WAL-Modus |
| Namespace-Konflikte | Jede Bridge hat exklusiven Regex in registration.yaml |

---

## Abhaengigkeiten

- exec-05 Phase A abgeschlossen (NATS-Pfad funktioniert)
- exec-05 Phase B abgeschlossen (E2EE im Go Appservice aktiv)
- Tuwunel laeuft und akzeptiert mehrere Appservice-Registrierungen
- NATS JetStream laeuft
- Fuer jede Bridge: ein Account auf der jeweiligen Plattform zum Testen

---

## Zu evaluieren: Nicht-Messenger Bridges

### DevOps / Projekt-Management

| Bridge | Was | Status | Relevanz |
|--------|-----|--------|----------|
| **Matrix Hookshot** | GitHub, GitLab, JIRA, Generic Webhooks | Production-ready, E2BE stabil | Hoch — Agent kann auf CI/CD Events, Issues, PRs reagieren |
| **maubot** | Bot-Framework mit Plugin-System (RSS, Reminder, Translate, etc.) | Production-ready | Mittel — erweiterbare Bot-Plattform |
| **Matterbridge** | 30+ Plattformen (IRC, Slack, Mattermost, Rocket.Chat, Twitch, Zulip, VK...) | Stabil, Bot-Style (kein Puppeting) | Niedrig — breite Abdeckung aber keine tiefe Integration |

### Kommunikations-Protokolle

| Bridge | Was | Status | Relevanz |
|--------|-----|--------|----------|
| **Heisenbridge** | IRC <-> Matrix | Stabil | Niedrig — Legacy, aber aktive IRC-Communities |
| **Bifroest** | XMPP/Jabber <-> Matrix | Maintained | Niedrig — wenige User, aber EU-Regierungen nutzen XMPP |
| **mautrix-gmessages** | Google Messages (RCS) <-> Matrix | Beta | Mittel — Android Default-Messenger |

### Content Feeds

| Bridge | Was | Status | Relevanz |
|--------|-----|--------|----------|
| **RSS/Atom Bot** (maubot plugin) | Feeds -> Matrix Room | Stabil | Mittel — News-Feeds als Agent-Kontext |
| **Matrix Hookshot Feeds** | RSS/Atom via Hookshot | Stabil | Mittel — Teil von Hookshot, kein extra Service |

### TODO: Evaluation
- [ ] Matrix Hookshot evaluieren (GitHub/GitLab Events -> Agent-Kontext)
- [ ] maubot evaluieren (RSS Feeds, Custom Plugins)
- [ ] Matterbridge evaluieren (falls Slack/IRC/Twitch Bedarf)
- [ ] mautrix-gmessages evaluieren (RCS/Google Messages)

---

## Content-Ingestion (nicht Matrix-spezifisch)

Externe Inhalte als Agent-Kontext in die App bringen.
Alle Tools muessen **kostenlos / Open-Source / Free-Tier** sein.

### Genereller Ingestion-Flow
```
Quelle (Email/YouTube/Website/RSS/PDF/...)
  ──> Ingestion Service (parst, konvertiert zu Markdown/Text)
  ──> Agent Context Store (ChromaDB Vector DB / Memory Service)
  ──> Optional: Summary -> Matrix Room (User-Sichtbarkeit)
  ──> Agent nutzt RAG um Fragen zu beantworten
```

---

### 1. Email-Ingestion

**Usecase:** Newsletter (z.B. Doomberg — Top-Finance/Energy, 372K Subscriber auf Substack),
Research-Reports, Alerts als Agent-Kontext.

**Architektur-Optionen:**

| Option | Flow | Pro | Contra |
|--------|------|-----|--------|
| **A: Postmoogle** | Gmail Forward -> SMTP -> Matrix Room -> Agent | Alles in Matrix | Braucht eigene Domain + MX-Records |
| **B: Direkt** | Gmail API / IMAP / Forward-Webhook -> Ingestion Service -> Vector DB | Einfach, direkte Kontrolle | Eigener Service |
| **C: Hybrid** | Ingestion -> Vector DB + Summary in Matrix Room | Bestes aus A+B | Zwei Pfade |

**Kostenlose Tools:**
- Gmail API (kostenlos, 1B Quota/Tag)
- IMAP (Standard, jeder Provider)
- Postmoogle (OSS, Go) — https://github.com/etkecc/postmoogle

**Features:**
- [ ] Absender-Whitelist (z.B. `newsletter@doomberg.com`, Gmail-Labels)
- [ ] HTML-to-Markdown Konvertierung
- [ ] Attachment-Extraktion (PDFs, Charts)
- [ ] Metadata (Datum, Betreff, Absender)
- [ ] Deduplizierung
- [ ] -> Vector DB (ChromaDB) als Knowledge-Chunks

**Beispiel-Flow: Doomberg Newsletter**
```
Doomberg published -> Email in Gmail -> Ingestion Service -> HTML->Markdown
-> ChromaDB als Chunk -> User fragt Agent "Energiemarkt?" -> RAG -> Antwort mit Kontext
```

---

### 2. YouTube-Ingestion

**Usecase:** Video-Transkripte von Finanz-/Tech-Channels als Agent-Kontext.
Z.B. Earnings Calls, Podcasts, Konferenz-Talks, Tutorials.

**Kostenlose Tools:**

| Tool | Was | Kosten | Anmerkung |
|------|-----|--------|-----------|
| **youtube-transcript-api** | Python Lib, holt Untertitel/Transkripte | Kostenlos, OSS, kein API-Key | Funktioniert mit auto-generated Subtitles |
| **yt-dlp** | CLI, laedt Subtitles/Metadata/Audio | Kostenlos, OSS | Kann auch nur Metadata + Subtitles holen (kein Video noetig) |
| **Whisper** (OpenAI, lokal) | Audio -> Text (STT) | Kostenlos, lokal | Fuer Videos ohne Untertitel: Audio extrahieren -> Whisper |

**Flow:**
```
YouTube URL / Channel / Playlist
  -> youtube-transcript-api (Untertitel holen)
  -> Falls keine Untertitel: yt-dlp Audio -> Whisper lokal
  -> Markdown mit Timestamps
  -> ChromaDB als Knowledge-Chunks
```

**Features:**
- [ ] Channel/Playlist-Subscription (periodisch neue Videos pruefen)
- [ ] Transkript mit Timestamps (fuer Referenz-Links)
- [ ] Metadata (Titel, Channel, Datum, Views, Beschreibung)
- [ ] Whisper-Fallback fuer Videos ohne Subtitles

---

### 3. Website-/Artikel-Ingestion

**Usecase:** Blog-Posts, Research-Artikel, Dokumentation, News-Seiten
als Agent-Kontext scrapen und indexieren.

**Kostenlose Tools:**

| Tool | Was | Kosten | Anmerkung |
|------|-----|--------|-----------|
| **Crawl4AI** | OSS Web-Crawler, Playwright-basiert, LLM-aware Chunking | Kostenlos, OSS, lokal | Bester kostenloser Scraper fuer RAG (2026 SOTA) |
| **Jina Reader** | URL -> LLM-ready Markdown (`r.jina.ai/URL`) | Free Tier (begrenzt) | Super fuer Prototyping, kein Self-Host |
| **Firecrawl** | Web -> Markdown, rekursives Crawling | OSS Self-Host kostenlos, Cloud kostenpflichtig | Self-Host via Docker |
| **trafilatura** | Python Lib, extrahiert Artikel-Text aus HTML | Kostenlos, OSS | Leichtgewichtig, kein Browser noetig |
| **mozilla/readability** | JS Lib (wie Firefox Reader View) | Kostenlos, OSS | Standard fuer Artikel-Extraktion |

**Flow:**
```
URL oder URL-Liste
  -> Crawl4AI / trafilatura / Jina Reader
  -> HTML -> Clean Markdown (Artikel-Text, keine Ads/Navigation)
  -> Metadata (Titel, Autor, Datum, URL)
  -> ChromaDB als Knowledge-Chunks
```

**Features:**
- [ ] URL-Watchlist (periodisch auf Updates pruefen)
- [ ] Sitemap-Crawling (ganze Docs-Seiten indexieren)
- [ ] Robots.txt respektieren
- [ ] Rate-Limiting (hoefliches Scraping)

---

### 4. RSS/Atom Feed Ingestion

**Usecase:** News-Feeds, Blog-Updates, Substack-Posts automatisch ingestieren.

**Kostenlose Tools:**

| Tool | Was | Kosten |
|------|-----|--------|
| **feedparser** | Python Lib, parst RSS/Atom | Kostenlos, OSS |
| **maubot RSS plugin** | Matrix Bot, postet Feed-Items in Raum | Kostenlos, OSS |
| **Matrix Hookshot** | RSS/Atom als Feature integriert | Kostenlos, OSS |

**Flow:**
```
RSS Feed URL (z.B. Doomberg Substack, Hacker News, ArXiv)
  -> feedparser (periodisch pollen)
  -> Artikel-URL extrahieren -> Crawl4AI/trafilatura fuer Volltext
  -> ChromaDB als Knowledge-Chunks
  -> Optional: Summary in Matrix Room
```

---

### 5. PDF-/Dokument-Ingestion

**Usecase:** Research Papers, Whitepapers, Earnings Reports als Agent-Kontext.

**Kostenlose Tools:**

| Tool | Was | Kosten |
|------|-----|--------|
| **PyMuPDF (fitz)** | PDF -> Text/Markdown, Tabellen, Bilder | Kostenlos, OSS |
| **pdfplumber** | PDF -> Text mit Layout-Erhaltung | Kostenlos, OSS |
| **marker** | PDF -> Markdown (ML-basiert, beste Qualitaet) | Kostenlos, OSS, lokal |
| **docling** (IBM) | PDF/DOCX/PPTX -> Markdown, Tabellen, Formeln | Kostenlos, OSS |
| **unstructured** | Multi-Format Parser (PDF, DOCX, HTML, etc.) | OSS Core kostenlos |

**Flow:**
```
PDF Upload oder URL
  -> marker / PyMuPDF / docling
  -> Markdown mit Tabellen und Bildern
  -> ChromaDB als Knowledge-Chunks
```

---

### 6. Podcast/Audio-Ingestion

**Usecase:** Podcast-Episoden, Earnings Calls, Interviews transkribieren.

**Kostenlose Tools:**

| Tool | Was | Kosten |
|------|-----|--------|
| **Whisper** (OpenAI, lokal) | Audio -> Text, multilingual | Kostenlos, OSS, lokal |
| **faster-whisper** | Whisper mit CTranslate2 (4x schneller) | Kostenlos, OSS |
| **podcastparser** | Podcast RSS -> Episode-Metadata + Audio-URL | Kostenlos, OSS |

**Flow:**
```
Podcast RSS Feed
  -> podcastparser (neue Episoden erkennen)
  -> Audio downloaden
  -> faster-whisper -> Transkript mit Timestamps
  -> ChromaDB als Knowledge-Chunks
```

---

### 7. Code-Repository Ingestion

**Usecase:** Dokumentation, Issues, Changelogs von GitHub/GitLab Repos als Kontext.

**Kostenlose Tools:**

| Tool | Was | Kosten |
|------|-----|--------|
| **GitHub API** | Repos, Issues, PRs, Discussions, READMEs | Kostenlos (5000 req/h authenticated) |
| **Matrix Hookshot** | GitHub/GitLab Webhooks -> Matrix Room | Kostenlos, OSS |
| **gitingest** | Repo -> single Markdown file fuer LLM | Kostenlos, OSS |

---

### 8. Financial Data Ingestion (kostenlos)

**Usecase:** Marktdaten, SEC Filings, Earnings als Agent-Kontext.

| Tool | Was | Kosten |
|------|-----|--------|
| **yfinance** | Yahoo Finance API (Kurse, Fundamentals) | Kostenlos, OSS |
| **SEC EDGAR API** | SEC Filings (10-K, 10-Q, 8-K) | Kostenlos, offiziell |
| **FRED API** | Federal Reserve Economic Data | Kostenlos (API Key) |
| **OpenBB** | Open-Source Bloomberg-Alternative, Terminal + SDK | Kostenlos, OSS |
| **Alpha Vantage** | Aktien, Forex, Crypto API | Free Tier (25 req/Tag) |

---

### TODO: Content-Ingestion (alle Quellen)
- [ ] Architektur-Entscheidung: Zentraler Ingestion-Service vs. pro-Quelle Worker
- [ ] ChromaDB Integration mit Memory Service planen (existiert bereits)
- [ ] Ingestion-Scheduler (Cron/Polling-Intervalle pro Quelle)
- [ ] Absender/Quellen-Whitelist UI im Control Panel
- [ ] Deduplizierung Cross-Source (gleicher Artikel via RSS + Email)
- [ ] Evaluieren:
  - [ ] youtube-transcript-api + yt-dlp
  - [ ] Crawl4AI vs. trafilatura vs. Jina Reader (Free Tier)
  - [ ] feedparser + Hookshot RSS
  - [ ] marker vs. docling vs. PyMuPDF fuer PDFs
  - [ ] faster-whisper fuer Audio/Podcast
  - [ ] yfinance + SEC EDGAR + OpenBB fuer Financial Data
  - [ ] gitingest fuer Code-Repos

---

## DMA-Watch (Zukunft)

Element arbeitet an offizieller WhatsApp<->Matrix Interoperabilitaet via DMA APIs.
Stand 03/2026: 1:1 Chats funktionieren mit E2EE, aber noch nicht Production-ready.
Wenn DMA-API stabil wird, koennte sie mautrix-whatsapp (Reverse-Engineered) ersetzen.
Monitoring: https://element.io/blog/the-eu-digital-markets-act-is-here/
