# TREK — Evaluation & Takeaways

> Evaluiert am 02.04.2026 | Repo: https://github.com/mauriceboe/TREK | Lizenz: AGPL-3.0

## Was ist TREK?

Selbstgehosteter, kollaborativer Reiseplaner — Privacy-respektierende Alternative zu Wanderlog/TripIt. Alles in einem Docker-Container. 3.057 Stars in 14 Tagen.

## Tech Stack

| Layer | Technologie |
|---|---|
| Backend | Node.js 22 + Express + TypeScript |
| Database | SQLite via better-sqlite3 |
| Frontend | React 18 + Vite + Tailwind CSS |
| Real-time | WebSocket (native `ws`) |
| PWA | vite-plugin-pwa + Workbox |
| State | Zustand |
| Auth | JWT (httpOnly cookies) + OIDC + TOTP MFA |
| Maps | Leaflet + react-leaflet-cluster (OSM default, Google Places optional) |
| Weather | Open-Meteo API (free, no key) |
| Deploy | Single Docker image |

## Was koennen wir mitnehmen?

### 1. MCP Integration Pattern
TREK exponiert `search_place` und `list_categories` als MCP Tools. AI-Agents koennen direkt mit der App interagieren. **Fuer unser Projekt relevant:** Gleicher Ansatz fuer geopolitische Datenquellen — MCP Tools exponieren die KG-Query-API.

### 2. Single-Container Monolith
Express + SQLite + WebSocket + Static Build in einem Image. Zwei Volumes (`./data`, `./uploads`), ein `docker run` Command. **Takeaway:** Fuer Self-Hosting-Tools ist Einfachheit > Microservices. Unser Agent-Backend koennte aehnlich simpel deployed werden.

### 3. Zero-Cost API Defaults
Open-Meteo (Wetter, kein Key) + OSM (Karten, kein Key) = funktioniert out-of-the-box ohne Config. Google Places ist opt-in. **Takeaway:** Default auf freie APIs, kommerzielle als Upgrade-Pfad.

### 4. Addon-System
Modulare Features (Vacay, Atlas, Collab) die Admins togglen koennen. Core bleibt schlank. **Takeaway:** Feature-Modularisierung ueber Admin-Toggles statt Feature-Flags im Code.

### 5. Security-Response-Velocity
v2.7.2 (Tag 12) hatte: JWT→httpOnly Migration, AES-256-GCM at-rest, SSRF-Schutz, CSP-Hardening, RCE-Fix. Externer Security-Audit von Community-Researchern wurde sofort umgesetzt. **Takeaway:** Bei oeffentlichem Launch sofort Security-Feedback ernst nehmen.

### 6. WebSocket Real-Time Collab
Native `ws` statt Socket.io — weniger Overhead. Jeder Trip ist ein separater WS-Channel. **Takeaway:** Fuer unsere Agent-Chat-Architektur: nativer WS statt Abstraktionslayer wenn Performance zaehlt.

### 7. PWA mit Offline-Support
Workbox cached Map-Tiles, API-Responses, Uploads. Vollstaendig offline-faehig. **Takeaway:** Fuer Mobile-First Agent-Interfaces relevant.

## Bedenken / Was NICHT mitnehmen

- SQLite als einzige DB → Skalierungs-Ceiling. Fuer uns: PostgreSQL/FalkorDB bleiben die richtige Wahl.
- 16 Releases in 14 Tagen → fruehe Versionen hatten echte Sicherheitsluecken. Kein Vorbild fuer Release-Cadence.
- Bus-Factor ~1.5 → Nicht nachahmenswert fuer kritische Infrastruktur.

## Architektur-Diagramm (vereinfacht)

```
[React PWA + Leaflet] ──── WS ────── [Express + ws]
         │                                  │
    Vite Build                         better-sqlite3
         │                                  │
    Static Files                      ./data/trek.db
         │
    Workbox Cache                     ./uploads/
```

## Links

- Demo: https://demo-nomad.pakulat.org
- Docker Hub: `mauriceboe/trek`
- Releases: 16 Releases in 14 Tagen (v2.1.0 bis v2.7.2)
