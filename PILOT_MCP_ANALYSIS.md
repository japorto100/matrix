# Pilot MCP — Browser-Automation fuer AI Agents

> Analysiert am 02.04.2026 | Repo: https://github.com/TacosyHorchata/Pilot | Lizenz: MIT

## Was ist Pilot?

Ein TypeScript/Node.js MCP-Server der auf Playwright aufbaut und AI-Agents Zugriff auf den **echten Chrome-Browser** gibt — mit bestehenden Login-Sessions. KEIN Playwright-Clone, NICHT in Rust geschrieben.

**Kernidee:** "Dein AI-Agent steuert einen Tab in deinem echten Chrome — bereits eingeloggt, keine Bot-Erkennung, keine CAPTCHAs."

## Architektur

### Extension Mode (primaer)
```
AI Agent → MCP stdio → Pilot Node → WebSocket :3131 → Chrome Extension → Echter Chrome Tab
```

### Headed Mode (Fallback)
Wenn keine Extension verbunden → Playwright-Chromium startet direkt.

### Source Layout
```
src/
├── index.ts               # MCP Server Entry, Tool Registration
├── browser-manager.ts     # Browser Lifecycle, Ref Map, Tab Tracking
├── extension-server.ts    # Broker/Client WS Multiplexer
├── snapshot.ts            # Accessibility Tree Serialization
├── buffers.ts             # Circular Ring Buffers (Console/Network/Dialog)
├── cookie-import.ts       # Chrome/Arc/Brave/Edge SQLite + Keychain Decryption
├── url-validation.ts
├── types.ts
└── tools/
    ├── register.ts        # Profile-basiertes Tool-Loading (core/standard/full)
    ├── navigation.ts      # pilot_navigate, pilot_get, pilot_back
    ├── snapshot-tools.ts  # pilot_snapshot, pilot_snapshot_diff, pilot_find
    ├── interaction.ts     # pilot_click, pilot_fill, pilot_type, pilot_drag
    ├── inspection.ts      # pilot_page_text, pilot_page_html, pilot_page_forms
    ├── automation.ts      # pilot_intercept, pilot_assert, pilot_clipboard
    ├── tabs.ts
    ├── iframe.ts
    ├── visual.ts          # pilot_screenshot, pilot_pdf, pilot_responsive
    ├── settings.ts        # pilot_block, pilot_geolocation, pilot_set_header
    └── page.ts
extension/
├── background.js          # Service Worker — WS Client to Broker
├── content.js             # DOM Interaction Scripts
├── manifest.json
└── popup.html/js
```

## Vergleich mit @playwright/mcp (Microsoft)

| Dimension | Pilot | @playwright/mcp |
|---|---|---|
| Echte Browser-Kontrolle | Chrome Extension, echter Tab | Separates Chromium |
| Bot/CAPTCHA | Kein Problem (echter Fingerprint) | Oft geblockt (Cloudflare) |
| Cookie-Import | Entschluesselt Chrome/Arc/Brave/Edge | Manuelles JSON-Export |
| Navigate Output | ~842 Chars | ~58.325 Chars |
| Token-Verbrauch | **69x weniger** | Frisst Context-Window |
| CAPTCHA-Handoff | pilot_handoff → Mensch loest → Agent weiter | Nicht verfuegbar |
| Multi-Agent | Broker/Client Multiplexer, Tab-Gruppen | Nicht verfuegbar |
| Snapshot-Diffing | pilot_snapshot_diff | Nicht verfuegbar |
| Iframe-Support | pilot_frames, pilot_frame_select | Nicht verfuegbar |
| Tools | 61 (core/standard/full) | 22 |
| Windows Cookie-Import | Nein (nur macOS/Linux) | Ja |
| Transport | Nur stdio | stdio, HTTP, SSE |
| Browser-Support | Nur Chromium | Chrome, Firefox, WebKit |

## Ref-Based Element Addressing

Pilot nutzt ein `@eN` / `@cN` Referenz-System:
```
pilot_snapshot() → Accessibility Tree mit @e14, @e15, @c3 Refs
pilot_click({ref: "@e14"}) → Klickt Element ueber In-Memory RefMap
```

Stabiler als CSS-Selektoren, schneller als DOM-Re-Query.

## Performance (Benchmarks auf news.ycombinator.com)

| Operation | Pilot | @playwright/mcp |
|---|---|---|
| Navigate (End-to-End) | 2.433ms, 842 Chars | 4.354ms, 58.325 Chars |
| Snapshot | ~17ms | N/A |
| Screenshot | 70-201ms | N/A |
| page_text | 2ms | N/A |

**"5ms per action" Claim** bezieht sich auf In-Memory-Operationen, nicht End-to-End.

## Broker/Client Multiplexer

```
Chrome Extension ←── WS ──→ Broker (erster Pilot-Prozess, Port 3131)
                              ├── Client 1 (Claude Code Session A) → Tab Gruppe Blau
                              ├── Client 2 (Claude Code Session B) → Tab Gruppe Gruen
                              └── Client 3 (Cursor Session) → Tab Gruppe Rot
```

Token: `~/.pilot/broker-token` (mode 0600).

## Security-Bedenken

- Extension lauscht auf `ws://127.0.0.1:3131` — lokale Prozesse koennten verbinden
- `pilot_evaluate` fuehrt beliebiges JavaScript im echten Browser aus (50KB Limit)
- `pilot_import_cookies` entschluesselt Chrome Cookie-DB via OS Keychain — maechtig aber riskant
- Cookie-Import nur macOS/Linux

## Relevanz fuer unser Projekt

### Direkt nutzbar:
- **OSINT-Recherche**: Agent navigiert authentifizierte Quellen (hinter Logins)
- **Token-Effizienz**: 69x Reduktion bei Multi-Step Web-Workflows
- **CAPTCHA-Handoff**: Mensch-in-the-Loop fuer schwierige Seiten

### Architektur-Inspiration:
- **Accessibility Tree als State-Repraesentation** statt Raw HTML
- **Ref-System** fuer stabile Element-Referenzen
- **Snapshot-Diffing** fuer inkrementelle State-Updates

### Einschraenkungen:
- 8 Tage alt, v0.4.x, ein Hauptentwickler
- Major Architecture Pivot an Tag 5
- Kein Windows Cookie-Import
- Nur stdio Transport

## Links

- Repo: https://github.com/TacosyHorchata/Pilot
- npm: `pilot-mcp` v0.4.2
- Entwickler: Pedro E. Rios + Ruben Ramirez
- Stars: 29 (8 Tage alt)
