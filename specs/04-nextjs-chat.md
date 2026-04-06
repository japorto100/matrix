# Next.js Embedded Matrix Chat UI

**Status:** Aktiv
**Stand:** 06.04.2026 — Phase 2-4 abgeschlossen, agent-chat als separates Feature-Modul integriert

## Konzept

Ein `"use client"` React-Komponenten-Set, das **matrix-js-sdk v41** im Browser nutzt.
Eigene UI mit **Tailwind v4 + shadcn/ui** (identisch zum Hauptprojekt-Theme).
Kein matrix-react-sdk (zu schwer, nicht Tailwind-kompatibel).

**Zwei Komponenten-Sets:**
1. `nextjs-chat/src/components/matrix/` — Matrix Chat (45+ Komponenten)
2. `agent-chat/src/components/` — Agent Chat (AssistantUI + Tambo + tldraw + Novel)

Beide werden im selben Frontend gemounted (`agent-chat` als Feature-Modul fuer
Generative AI Chat, `matrix/` fuer Peer-to-Peer + Bot Chat).

---

## Stack & Versionen

**Core:**
- Next.js **16.2.1** (Webpack — Turbopack UV-Bug auf Windows)
- React **19.2.4** + React DOM
- TypeScript **5.9.3**
- Tailwind CSS **4.2.2** + `@tailwindcss/postcss`
- matrix-js-sdk **41.2.0**

**UI-Bibliotheken:**
- shadcn/ui — **46 Komponenten** (Radix UI), siehe `components.json`
- lucide-react — Icons
- framer-motion **12.38.0** + `@formkit/auto-animate`
- sonner — Toast Notifications

**Editor & Rich Text:**
- @tiptap/react **3.21** + starter-kit + extension-code-block + extension-mention + extension-placeholder
- react-markdown **10.1** + remark-gfm + rehype-sanitize + rehype-raw + rehype-stringify
- react-shiki — VS Code Syntax Highlighting
- emoji-mart **5.6** + @emoji-mart/react + @emoji-mart/data

**Document Preview:**
- react-pdf **10.4** — PDF
- docx-preview **0.3.7** — DOCX
- xlsx — Spreadsheet Export

**Voice/Video:**
- @livekit/components-react **2.9.20** + livekit-client **2.18** + @livekit/track-processors

**State & Data:**
- zustand **5.0** — State Management
- @tanstack/react-query **5.94** — Data Fetching
- @tanstack/react-virtual **3.13** — Virtualized Timeline
- nuqs — URL State

**Forms & Validation:**
- react-hook-form **7.72** + @hookform/resolvers
- zod **4.3**

**Misc:**
- qrcode **1.5** — QR Codes (Verification)
- browser-image-compression **2.0** — Upload-Optimierung
- uuid

**Dev:**
- @biomejs/biome **2.3.15** (Linter + Formatter)

---

## Implementierter Feature-Stand

### Message-Typen (vollstaendig)

| Typ | Beschreibung | Status |
|---|---|---|
| `m.text` | Text + Markdown + Code Highlighting (react-shiki) | ✅ |
| `m.notice` | System-Notices (kursiv, gedaempft) | ✅ |
| `m.emote` | `/me`-Stil Aktions-Nachrichten | ✅ |
| `m.image` | Bild mit Lightbox | ✅ |
| `m.video` | HTML5 Video-Player + Poster | ✅ |
| `m.audio` | Audio + Sprachnachrichten (MSC3245) | ✅ |
| `m.file` | Datei-Download mit Icon, Groesse, MIME | ✅ |
| `m.location` | Standort → OpenStreetMap-Link | ✅ |
| `m.sticker` | Sticker (MSC2545) | ✅ |
| Redacted | Platzhalter | ✅ |
| Document Preview | PDF (react-pdf), DOCX (docx-preview), Markdown | ✅ |

### Relations & Interaktionen

| Feature | Beschreibung | Status |
|---|---|---|
| Reaktionen (m.reaction) | Aggregiert nach Emoji + User-Tracking | ✅ |
| Reply-Kontext | in_reply_to Banner ueber der Nachricht | ✅ |
| Threads (MSC3440) | Vollstaendige Thread-Unterstuetzung mit ThreadPanel + ThreadOverview | ✅ |
| Bearbeitet-Badge | `(bearbeitet)` wenn `replacingEvent()` | ✅ |
| Typing-Indikator | "Agent tippt…" mit 3s Debounce | ✅ |
| Pagination | Aeltere Nachrichten via `scrollback()` | ✅ |
| Virtualized Timeline | @tanstack/react-virtual | ✅ |
| Datei-Upload | Bild/Video/Audio/Datei + Compression | ✅ |
| Pinned Messages | `usePinnedMessages` Hook + Power-Level Check | ✅ |
| Forward / Redact / Edit | Vollstaendiger Action Context Menu | ✅ |
| Read Receipts | Mini-Initials-Kreise unter eigenen Nachrichten | ✅ |
| Mention-Highlight | MSC3952 `m.mentions.user_ids` | ✅ |
| URL Preview | `UrlPreview`-Komponente + Auth-Proxy | ✅ |

### UI / UX

| Feature | Status |
|---|---|
| shadcn/ui Komponenten (46) | ✅ |
| Multi-Theme (dark/blue-dark/green-dark) | ✅ |
| Raum-Liste mit Ungelesen-Badge + Presence-Dot | ✅ |
| Skeleton Loading State | ✅ |
| Auto-Scroll bei neuen Nachrichten | ✅ |
| Shift+Enter Zeilenumbruch | ✅ |
| WYSIWYG Editor (Tiptap) mit @-Mentions, Code-Blocks, Placeholders | ✅ |
| Activity Centre | ✅ |
| Search Panel | ✅ |
| Keyboard Shortcuts (Alt+C New Room, Cmd+K Search) | ✅ |
| Notifications (Desktop + Browser + Unread Badge) | ✅ |
| Mute Room | ✅ |

### Spaces & Rooms (MSC1772)

| Feature | Status |
|---|---|
| SpaceSelector | ✅ |
| SpaceSettings | ✅ |
| CreateSpaceDialog | ✅ |
| Room-zu-Space Zuweisung | ✅ |

### Polls (MSC3381)

| Feature | Status |
|---|---|
| PollMessage Renderer | ✅ |
| CreatePollDialog | ✅ |
| `usePoll` Hook (Last-Vote-Wins Deduplizierung) | ✅ |

### Voice/Video Calls (MatrixRTC + LiveKit)

| Feature | Status |
|---|---|
| LiveKit als RTC Transport (well_known.rtc_transports) | ✅ |
| `useMatrixRTCCall` Hook (Token Generation, Call State) | ✅ |
| `CallOverlay` mit Grid + Controls + Screen Share | ✅ |
| Background Blur (Track Processor) | ✅ |
| Group Calls (MSC3401) | ✅ |

### E2EE (Phase 2-4)

| Feature | Status |
|---|---|
| Rust Crypto (vodozemac → WASM) | ✅ |
| `initRustCrypto()` aktiv | ✅ |
| Cross-Signing (MSC4153) | ✅ |
| `useCrossSigning` Hook | ✅ |
| QR-Code Verification (Byte-Segment) | ✅ |
| SAS-Emoji-Fallback | ✅ |
| EncryptionBadge UI | ✅ |
| `globalBlacklistUnverifiedDevices = false` (Dev) | ⚠️ Production-TODO |
| Megolm Key Backup | ❌ siehe FUTURE_IDEAS.md |

### Sliding Sync (MSC3575)

| Feature | Status |
|---|---|
| Tuwunel `simplified_msc3575` aktiv | ✅ |
| Range [[0, 99]] Initial Load | ✅ |
| Timeline Limit 50 | ✅ |
| Presence Extension | ✅ |

### Agent Detection

| Feature | Status |
|---|---|
| `isAgentUser()` (NEXT_PUBLIC_MATRIX_AGENT_PREFIX, default `@agent-`) | ✅ |
| Agent-Badge in MentionList | ✅ |
| Auto-Accept Invites (fuer Bot-User) | ✅ |

---

## Verzeichnisstruktur (`nextjs-chat/`)

```
src/
├── components/
│   ├── ui/                              # 46 shadcn/ui Komponenten
│   │   ├── button.tsx, card.tsx, dialog.tsx, popover.tsx, ...
│   │
│   └── matrix/                          # 45+ Matrix Komponenten
│       ├── MatrixProvider.tsx           # Client Init + Sliding Sync + Rust Crypto
│       ├── MatrixAppClient.tsx
│       ├── MatrixChat.tsx               # Main orchestrator
│       ├── Timeline.tsx                 # Virtualisierte Timeline
│       ├── Message.tsx
│       ├── MessageComposer.tsx
│       ├── RoomHeader.tsx
│       ├── TypingIndicator.tsx
│       ├── CallOverlay.tsx              # MatrixRTC + LiveKit
│       ├── CrossSigningSetup.tsx        # E2EE Verification UI
│       ├── EmojiPicker.tsx
│       ├── ForwardDialog.tsx
│       ├── ReadByDialog.tsx
│       ├── SearchPanel.tsx
│       ├── ActivityCentre.tsx
│       ├── UserProfileDialog.tsx
│       ├── DMInfoPanel.tsx
│       ├── UrlPreview.tsx
│       ├── ErrorBoundary.tsx
│       ├── CreateRoomDialog.tsx
│       ├── CreatePollDialog.tsx
│       ├── PollMessage.tsx
│       ├── room-list/                   # RoomList, RoomItem, InviteItem
│       ├── room-info/                   # RoomInfoPanel, AdminSettings, MemberList, SharedMedia
│       ├── threads/                     # ThreadPanel, ThreadOverview (MSC3440)
│       ├── message/                     # MessageContent, MessageActions, Reactions, content/{Media,Text,File,Location}
│       ├── composer/                    # WysiwygEditor (Tiptap), MentionList
│       ├── spaces/                      # SpaceSelector, SpaceSettings, CreateSpaceDialog
│       ├── contacts/                    # ContactPicker, CreateDMDialog, InviteDialog
│       └── shared/                      # EncryptionBadge, MatrixAvatar
│
├── lib/
│   ├── matrix/
│   │   ├── client.ts                    # matrix-js-sdk Singleton + IndexedDB Store + Rust Crypto
│   │   ├── types.ts                     # ResolvedMessage (45+ Fields), RoomInfo, MatrixCredentials
│   │   ├── utils.ts                     # mxcToHttp, mxcToThumbnail, formatFileSize
│   │   ├── resolvers.ts                 # Message/Room Resolver, isAgentUser()
│   │   ├── MatrixKeyProvider.ts         # Secure Key Storage
│   │   └── hooks/                       # 18 Custom Hooks (siehe naechste Sektion)
│
├── hooks/                               # Generelle React Hooks (nicht Matrix-spezifisch)
│
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── matrix/page.tsx                  # Server Component, lädt Credentials
│   ├── matrix/MatrixLoader.tsx
│   └── api/matrix/
│       ├── credentials/route.ts         # Credentials Endpoint
│       ├── media/route.ts               # Media Proxy/Download
│       └── preview/route.ts             # URL Preview Enrichment
```

---

## Custom Hooks in `lib/matrix/hooks/` (18)

| Hook | Funktion |
|---|---|
| `useMatrixClient` | Context-Hook fuer Client-Zugriff |
| `useTimeline` | Timeline-Loading mit Pagination + Reaction-Aggregation |
| `useThreadTimeline` | Thread-Timeline (MSC3440) mit separaten Page-Loading |
| `useRooms` | Raum-Liste + Filtern (Join/Invite/Leave State) |
| `useRoomMembers` | Member-Liste + Praesenz-Updates |
| `useTyping` | Typing-Indikatoren (3s Debounce) |
| `usePinnedMessages` | Pinned Events + Power-Level Check |
| `useMessageActions` | Reply, Edit, Redact, React, Forward Callbacks |
| `useNotifications` | Desktop + Browser Notifications + Unread Badge |
| `useMuteRoom` | Room-Mute Toggles |
| `useContacts` | User-Kontakt-Erfassung + Presence |
| `useSpaces` | Space-Navigation |
| `useCrossSigning` | E2EE Device-Verification (QR + SAS) |
| `useAutoAcceptInvites` | Auto-Accept Setup (fuer Bot-User) |
| `useKeyboardShortcuts` | Alt+C New Room, Cmd+K Search, etc. |
| `usePoll` | Poll Voting (MSC3381) |
| `useMatrixRTCCall` | MatrixRTC/LiveKit Integration |

---

## API Routes

| Route | Method | Funktion |
|---|---|---|
| `/api/matrix/credentials` | POST | Login/Credentials Handshake |
| `/api/matrix/media` | GET | Media Proxy (mxc:// → HTTP) |
| `/api/matrix/preview` | GET | URL Preview Enrichment |

Agent-spezifische Routen liegen im separaten `agent-chat/` Modul:
`/api/agent/chat`, `/api/agent/approve`, `/api/agent/completion`, `/api/audio/*`.

---

## E2EE im Browser (matrix-js-sdk)

matrix-js-sdk v41 laedt intern `@matrix-org/matrix-sdk-crypto-wasm` (Rust vodozemac → WASM).
Kein separater Import noetig.

```typescript
// src/lib/matrix/client.ts
const client = createClient({
  baseUrl: homeserverUrl,
  userId,
  accessToken,
  deviceId,
  timelineSupport: true,
});

// Rust WASM Crypto (vodozemac → IndexedDB Store)
await client.initRustCrypto();
client.getCrypto()!.globalBlacklistUnverifiedDevices = false; // Dev
```

**Status:**
- Rust Crypto aktiv, IndexedDB Store pro User pro Browser
- Cross-Signing-Verifikation via `CrossSigningSetup`-Komponente (QR + SAS)
- Production-TODO: `globalBlacklistUnverifiedDevices = true` (siehe FUTURE_IDEAS.md)

---

## mxc:// URL-Aufloesung

```typescript
export function mxcToHttp(mxcUrl: string, homeserverUrl: string): string {
  if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
  return `${homeserverUrl}/_matrix/media/v3/download/${mxcUrl.slice(6)}`;
}

export function mxcToThumbnail(
  mxcUrl: string, homeserverUrl: string, w=800, h=600
): string {
  if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
  return `${homeserverUrl}/_matrix/media/v3/thumbnail/${mxcUrl.slice(6)}?width=${w}&height=${h}&method=scale`;
}
```

**Authenticated Media (MSC3916):** Ab Tuwunel v0.4+ aktiv. Mit `allow_legacy_media = true`
in `tuwunel.toml` wird das alte Schema weiter unterstuetzt (QW-4). Migration auf
authenticated Media ist Future-Item, siehe FUTURE_IDEAS.md.

---

## next.config.ts

```typescript
const nextConfig: NextConfig = {
  // reactCompiler: true,  // deaktiviert: babel-plugin-react-compiler@1.0 / Windows UV-Bug
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

**Build-Status:**
- TypeScript ✅
- Biome-Lint ✅
- next build (Webpack) ✅
- Turbopack-Build ⚠️ — `Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)` (bekanntes Windows-Issue)

---

## Verhaeltnis zu agent-chat/

`nextjs-chat/` ist Matrix-fokussiert (E2EE Peer-to-Peer Chat). `agent-chat/` ist
ein separates Feature-Modul fuer den AI Chat (AssistantUI + Tambo + tldraw + Novel).

**Integration-Plan (exec-06):**
- agent-chat wird via `AgentChatPanel` als Modal/Side-Panel/Overlay in MatrixChat eingebunden
- Shared shadcn/ui Komponenten werden zwischen beiden geteilt
- Separate API Routes (`/api/matrix/*` vs. `/api/agent/*`)
- Beide nutzen das gleiche Python Backend (Port 8094 fuer Agent, Port 8090 via Go fuer Matrix)

Details zu `agent-chat/` in `agent-ui/01-architektur.md` und `agent-ui/02-features.md`.
