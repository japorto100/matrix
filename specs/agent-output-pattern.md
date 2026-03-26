# Agent Output Pattern für Mobile-Kompatibilität

Agents sollen Output so senden dass Element X / FluffyChat es gut darstellen können:

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

Die bestehenden Renderer (ImageContent, TextContent, FileContent) in `Message.tsx`
behandeln alle drei Typen bereits korrekt. Kein spezielles Bundling nötig.
