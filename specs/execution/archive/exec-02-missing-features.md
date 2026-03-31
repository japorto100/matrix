# Execution Slice 02 — ARCHIVIERT

> Vollständig ersetzt durch **exec-03-review-fixes.md** (25.03.2026).
> Alle 27 Feature-IDs aus diesem Dokument sind in exec-03 abgedeckt.

---

## Nachträglich identifizierte Lücken (aus ChatGPT-Forschung, 25.03.2026)

Folgende Punkte waren in exec-02 nicht enthalten und müssen in exec-03 aufgenommen werden:

1. **Spaces (MSC1772)** — Room-Hierarchien, `getRoomHierarchy`, `getRoomSummary`. SDK hat vollen Support. Für Gruppierung von Räumen (Teams, Märkte, Agenten). Komplett vergessen.
2. **`.well-known/matrix/client`** — Client-Discovery für Mobile-Apps. Ohne das findet Element X den Homeserver nicht über Domain. Für Tuwunel + Dendrite prüfen.
3. **MAS / OIDC Auth** — Matrix Authentication Service. QR-Code-Login, OAuth 2.0/OIDC. Zukunftsrichtung des Matrix-Auth-Stacks.
4. **Room-Management UI** — createRoom, publicRooms, Invite, kick, ban. Keine Oberfläche dafür vorhanden.
5. **Agent-Output-Format für Mobile** — Chart als PNG + Summary + CSV/PDF + Deep Link. Widgets nicht als primärer Pfad (Element X supportet sie noch nicht). Widget-Vorbereitung für wenn verfügbar.
6. **Agent Chat vs Matrix Chat Architektur** — Empfehlung: UI-Fusion, logisch getrennt (Option B). Dual Mode: Messenger in Matrix, Workspace in Webapp. Portierungs-Entscheidung.
