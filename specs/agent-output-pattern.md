# Agent Output Pattern fuer Mobile-Kompatibilitaet

**Status:** Aktiv
**Stand:** 06.04.2026 — Agent generiert Klartext, Go Appservice encrypted und sendet als Matrix Events

Agents sollen Output so senden dass Element X / FluffyChat es gut darstellen koennen:

1. Chart/Visualisierung: m.image (PNG/WebP) — wird als Bild inline angezeigt
2. Zusammenfassung: m.text mit formatted_body (HTML) — wird als formatierter Text gerendert
3. Rohdaten: m.file (CSV/PDF) — wird als Download-Link angezeigt
4. Deep Link: URL im Text-Body zurück zur Webapp für interaktive Ansicht

Kein Widget-Rendering (Element X supportet Widgets noch nicht).

## Sequenz

Ein Agent sendet pro Analyse-Anfrage typischerweise 3 Events in kurzer Folge:

```
1. m.room.message  msgtype: m.image   (Chart als PNG)
2. m.room.message  msgtype: m.text    (Zusammenfassung mit formatted_body)
3. m.room.message  msgtype: m.file    (CSV/PDF Rohdaten)
```

## Anforderungen an den Appservice / Bridge

- Bilder mit sinnvoller `body` (Caption) senden
- Text mit `format: "org.matrix.custom.html"` und `formatted_body` für Rich-Text
- Dateien mit korrektem `mimetype` in `info` und lesbarem `filename`
- Optional: Deep Link als letzte Zeile im Text-Body

## Rendering in nextjs-chat

Die bestehenden Renderer (`message/content/MediaContent.tsx`, `TextContent.tsx`,
`FileContent.tsx`) in `nextjs-chat/src/components/matrix/` behandeln alle drei Typen
bereits korrekt. Kein spezielles Bundling noetig.

---

## Streaming-Format (BFF — `agent-chat/`)

Im Web-Chat (nicht-Matrix) nutzt der Agent Service stattdessen das **Vercel AI Data
Stream Protocol** ueber SSE:

```
data: {"type":"thread_id","threadId":"..."}
data: {"type":"text_start","id":"..."}
data: {"type":"text_delta","id":"...","text":"..."}
data: {"type":"text_end","id":"..."}
data: {"type":"tool_start","name":"sandbox_execute"}
data: {"type":"tool_result","name":"sandbox_execute","content":"..."}
data: {"type":"finish","usage":{"input_tokens":...,"output_tokens":...}}
```

Die Python Bridge sammelt im Matrix-Pfad alle `text_delta` Events und sendet das
Ergebnis als ein `m.room.message` (mit optionalen `m.image` / `m.file` Events fuer
Tool-Outputs wie generierte Charts).

Details: `agent-ui/06-protocols-roadmap.md`, `03-python-agent-bridge.md`.
