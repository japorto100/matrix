# Next.js Embedded Matrix Chat UI

> Stand: 24.03.2026 — Phase 2 abgeschlossen

## Konzept

Ein `"use client"` React-Komponenten-Set, das matrix-js-sdk v41 im Browser nutzt.
Eigene UI mit **Tailwind v4 + shadcn/ui** (identisch zum Hauptprojekt-Theme).
Kein matrix-react-sdk (zu schwer, nicht Tailwind-kompatibel).

---

## Implementierter Feature-Stand

### Message-Typen (vollständig)

| Typ | Beschreibung | Status |
|---|---|---|
| `m.text` | Text, Markdown für Bot-Nachrichten | ✅ |
| `m.notice` | System-Notices (kursiv, gedämpft) | ✅ |
| `m.emote` | `/me`-Stil Aktions-Nachrichten | ✅ |
| `m.image` | Bild mit Lightbox (Klick → Vollbild) | ✅ |
| `m.video` | HTML5 Video-Player mit Poster | ✅ |
| `m.audio` | Audio-Player + Sprachnachrichten (MSC3245) | ✅ |
| `m.file` | Datei-Download mit Icon, Größe, MIME | ✅ |
| `m.location` | Standort → OpenStreetMap-Link | ✅ |
| `m.sticker` | Sticker-Bilder (MSC2545) | ✅ |
| Redacted | `[Nachricht gelöscht]` Platzhalter | ✅ |

### Relations & Interaktionen

| Feature | Beschreibung | Status |
|---|---|---|
| Reaktionen (m.reaction) | Aggregiert nach Emoji, Zähler angezeigt | ✅ |
| Reply-Kontext | in_reply_to Banner über der Nachricht | ✅ |
| Bearbeitet-Badge | `(bearbeitet)` wenn ev.replacingEvent() | ✅ |
| Typing-Indikator | "Agent tippt…" mit Animation | ✅ |
| Pagination | "Ältere Nachrichten laden" via scrollback() | ✅ |
| Virtualized Timeline | @tanstack/react-virtual (Performance) | ✅ |
| Datei-Upload | Bild/Video/Audio/Datei via Paperclip-Button | ✅ |

### UI / UX

| Feature | Status |
|---|---|
| Multi-Theme (dark/blue-dark/green-dark) | ✅ |
| Raum-Liste mit Ungelesen-Badge | ✅ |
| Skeleton Loading State | ✅ |
| Auto-Scroll bei neuen Nachrichten | ✅ |
| Shift+Enter Zeilenumbruch | ✅ |

### Phase 2 Features (QW-1 bis C-3)

| ID | Feature | Beschreibung | Status |
|---|---|---|---|
| QW-1 | `formatted_body` HTML-Rendering | `rehype-raw` + `rehype-sanitize` (defaultSchema + Matrix HTML Tags). `ReactMarkdown` schaltet zwischen `formattedBody` (HTML) und `body` (Markdown) | ✅ |
| QW-2 | Read Receipts senden | `client.sendReadReceipt(lastEv)` bei Raum-Fokus/Nachrichtenänderung (useEffect in MatrixChat) | ✅ |
| QW-3 | Mention-Highlight | MSC3952 `m.mentions.user_ids` → `isMentioned` auf ResolvedMessage → gelbe Bubble-Hervorhebung | ✅ |
| QW-4 | Legacy Media | `allow_legacy_media = true` in tuwunel.toml (Option A) | ✅ |
| C-1 | Sliding Sync | `SlidingSync` aus `matrix-js-sdk/lib/sliding-sync` (interner Import). An `startClient({ slidingSync })` übergeben. proxyBaseUrl=homeserverUrl, ranges [[0,99]], sort: notification_level+recency | ✅ |
| B-1 | Message Editing | `MessageComposer` erhält `EditState {eventId, body}` prop. Edit sendet `m.replace` Relation. ESC bricht ab. Edit-Banner angezeigt. Hover-Menü auf eigenen Nachrichten zeigt Edit-Button | ✅ |
| B-2 | Read Receipts visuell | `room.getReadReceiptForUserId()` pro Member, `readBy: string[]` auf ResolvedMessage, Mini-Initials-Kreise (3.5×3.5) unter eigenen Nachrichten | ✅ |
| B-3 | Reaktionen senden | Hover-Menü Emoji-Picker (8 Standard-Emojis), sendet `EventType.Reaction` + `RelationType.Annotation` | ✅ |
| B-4 | Redaction | Hover-Menü Delete-Button, ruft `client.redactEvent(roomId, eventId)` auf | ✅ |
| B-5 | URL-Vorschau | `UrlPreview`-Komponente, Next.js API Route `/api/matrix/preview` proxied Homeserver `/_matrix/client/v3/preview_url` mit Auth, module-scoped Cache | ✅ |
| B-6 | Presence | `allow_local_presence = true` in tuwunel.toml, `isOnline` auf RoomInfo, grüner Punkt auf Avatar in RoomList, `UserEvent.CurrentlyActive` + `UserEvent.Presence` Listener in useRooms | ✅ |
| B-9 | 1:1 Voice/Video Calls | `useCall` Hook mit vollständiger State Machine (idle/incoming/outgoing/connecting/connected/ended). `createNewMatrixCall`, `CallEventHandlerEvent.Incoming`, `CallState` aus internem Import. `CallOverlay`-Komponente (PiP-Stil). Telefon-/Video-Buttons in RoomHeader (nur DMs, memberCount <= 2) | ✅ |
| C-3 (Web) | Cross-Signing Setup | `useCrossSigning` Hook — prüft `isCrossSigningReady()`, behandelt `CryptoEvent.VerificationRequestReceived`, ruft `crypto.requestOwnUserVerification()` auf. `CrossSigningSetup`-Komponente: gelbes Banner + Modal. QR-Code via `request.generateQRCode()` → `qrcode`-Library (Byte-Segment-Modus). SAS-Emoji-Fallback. `VerificationRequestEvent.Change` für Phase-Watching | ✅ |

---

## Verzeichnisstruktur (nextjs-chat/)

```
src/
├── components/
│   ├── ui/                        # shadcn Komponenten
│   │   ├── avatar.tsx
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── dialog.tsx             # neu (Phase 2, C-3)
│   │   ├── scroll-area.tsx
│   │   ├── separator.tsx
│   │   ├── skeleton.tsx
│   │   └── textarea.tsx
│   │
│   └── matrix/
│       ├── CallOverlay.tsx        # neu (B-9) — PiP Voice/Video Call UI
│       ├── CrossSigningSetup.tsx  # neu (C-3) — QR-Verifikations-Banner + Modal
│       ├── MatrixAppClient.tsx    # Client-side Entry (dynamic import Wrapper)
│       ├── MatrixProvider.tsx     # Context Provider, Client-Init, Sync-Wait
│       ├── MatrixChat.tsx         # Haupt-Layout-Komponente
│       ├── Message.tsx            # Alle Message-Typen (image/video/audio/file/…)
│       ├── MessageComposer.tsx    # Textarea + Send + Datei-Upload + Edit-Modus
│       ├── RoomHeader.tsx         # Raum-Header (Name, Thema, Mitglieder, Call-Buttons)
│       ├── RoomList.tsx           # Raum-Liste mit Ungelesen-Badge + Presence-Dot
│       ├── Timeline.tsx           # Virtualisierte Nachrichten-Timeline
│       ├── TypingIndicator.tsx    # "Agent tippt…"
│       └── UrlPreview.tsx         # neu (B-5) — URL-Vorschau-Karte
│
├── lib/
│   └── matrix/
│       ├── client.ts              # matrix-js-sdk Client Factory (Singleton)
│       ├── types.ts               # ResolvedMessage, RoomInfo, mxcToHttp, …
│       └── hooks/
│           ├── useCall.ts         # neu (B-9) — Call State Machine
│           ├── useCrossSigning.ts # neu (C-3) — Cross-Signing Status + Verifikation
│           ├── useMatrixClient.ts # Client aus Context
│           ├── useRooms.ts        # Raum-Liste (reaktiv, event-driven, Presence)
│           ├── useTimeline.ts     # Timeline + Reaktion-Aggregation + Reply-Lookup
│           └── useTyping.ts       # Tipp-Indikator
│
└── app/
    ├── api/
    │   └── matrix/
    │       └── preview/
    │           └── route.ts       # neu (B-5) — URL-Preview Proxy mit Auth + Cache
    └── matrix/
        └── page.tsx               # Server Component, lädt Credentials aus .env
```

---

## package.json — Wichtige Abhängigkeiten

```json
{
  "dependencies": {
    "matrix-js-sdk": "^41.2.0",
    "@tanstack/react-virtual": "^3.13.23",
    "react-markdown": "^10.1.0",
    "rehype-raw": "^7.0.0",
    "rehype-sanitize": "^6.0.0",
    "remark-gfm": "^4.0.1",
    "qrcode": "^1.5.4",
    "date-fns": "^4.1.0",
    "lucide-react": "^0.525.0",
    "framer-motion": "^12.38.0",
    "next": "^16.2.1",
    "react": "^19.2.4"
  },
  "devDependencies": {
    "@types/qrcode": "^1.5.5",
    "babel-plugin-react-compiler": "^1.0.0",
    "@biomejs/biome": "2.3.15",
    "typescript": "^5.9.3"
  }
}
```

---

## E2EE im Browser (matrix-js-sdk)

matrix-js-sdk v41 lädt intern `@matrix-org/matrix-sdk-crypto-wasm` (Rust vodozemac → WASM).
Kein separater Import nötig.

```typescript
// src/lib/matrix/client.ts
const client = createClient({
  baseUrl: homeserverUrl,
  userId,
  accessToken,
  deviceId,
  timelineSupport: true,
});

// Rust WASM Crypto (vodozemac → IndexedDB Store) — AKTIV seit Phase 2
await client.initRustCrypto();
client.getCrypto()!.globalBlacklistUnverifiedDevices = false;
```

**E2EE-Status im Browser (Phase 2):**
- `initRustCrypto()` ist aktiv — matrix-sdk-crypto-wasm (vodozemac) läuft im Browser
- `globalBlacklistUnverifiedDevices = false` — sendet auch an unverifizierte Geräte (Dev-Modus)
- Key Store: IndexedDB (pro User, pro Browser)
- Cross-Signing-Verifikation via `CrossSigningSetup`-Komponente (QR-Code + SAS-Emoji-Fallback)
- `useCrossSigning` Hook überwacht Verifikationsstatus und initiiert Verifikationsflow

---

## mxc:// URL-Auflösung

Matrix Media-URLs beginnen mit `mxc://server/mediaId`.
Auflösung zu HTTP:

```typescript
// src/lib/matrix/types.ts
export function mxcToHttp(mxcUrl: string, homeserverUrl: string): string {
  if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
  return `${homeserverUrl}/_matrix/media/v3/download/${mxcUrl.slice(6)}`;
}

export function mxcToThumbnail(mxcUrl: string, homeserverUrl: string, w=800, h=600): string {
  if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
  return `${homeserverUrl}/_matrix/media/v3/thumbnail/${mxcUrl.slice(6)}?width=${w}&height=${h}&method=scale`;
}
```

**Achtung:** Ab Tuwunel v0.4+ ist Authenticated Media (MSC3916) aktiv.
Dann brauchen Media-Requests `Authorization: Bearer <access_token>`.
URL-Schema ändert sich auf `/_matrix/client/v1/media/download/`.
Mit `allow_legacy_media = true` in tuwunel.toml wird das alte Schema weiter unterstützt (QW-4).

---

## Bekannte Einschränkungen / TODOs

Alle Phase-2-Features (QW-1 bis B-9, C-3 Web-Seite) sind implementiert.

Verbleibende offene Punkte:

1. **D-1 — E2EE Vollbetrieb:** Browser sendet aktuell mit `globalBlacklistUnverifiedDevices=false`. Für Production: Vollständige Cross-Signing-Verifikation aller Geräte erzwingen.
2. **C-8 — Key Backup:** Neue Geräte können alte verschlüsselte Nachrichten nicht lesen (kein Megolm Key Backup implementiert).
3. **Phase 4 — Authenticated Media (MSC3916):** `allow_legacy_media = true` ist ein Workaround. Langfristig: Media-Requests mit Bearer-Token und neuem URL-Schema.
4. **Phase 4 — PQXDH:** Post-Quantum-Verschlüsselung erst bei Portierung auf vodozemac im Go Appservice (Production Linux).

---

## next.config.ts — Wichtige Einstellungen

```typescript
const nextConfig: NextConfig = {
  // reactCompiler: true,  // deaktiviert: babel-plugin-react-compiler@1.0.0 / Windows UV-Bug
  typedRoutes: true,
  reactStrictMode: true,
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.experiments = { ...config.experiments, asyncWebAssembly: true };
    }
    return config;
  },
};
```

**Build-Status:** TypeScript ✅ | Biome-Lint ✅ | next build ⚠️ (Turbopack UV-Bug auf Windows)
Turbopack-Build crasht mit `Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)` — bekanntes Windows-Issue.
Webpack-Build (ohne turbopack-Config) funktioniert.
