# exec2-01: Matrix Chat Core Features

> Konsolidiert aus exec-03 Sektionen 1+2 (Quick-Wins + Standard-Features)
> Stand: 30.03.2026

---

## Quick-Wins

### QW-1: formatted_body HTML Rendering
- [x] HTML-Rendering via unified + rehype-parse + rehype-sanitize
- [x] CSS-Injection Fix: filterMatrixStyle() (nur safe Properties)
- [x] Direktes HTML-Parsing statt ReactMarkdown fuer formatted_body

### QW-2: Read Receipts senden
- [x] client.sendReadReceipt() bei Raumwechsel + neuer Nachricht

### QW-3: Mention-Highlighting (MSC3952)
- [x] m.mentions.user_ids Auswertung + gelbes Highlight

### QW-4: Authenticated Media (MSC3916)
- [x] Next.js Media-Proxy /api/matrix/media
- [x] Legacy-Fallback fuer Homeserver ohne MSC3916
- [x] 24h Cache-Header

---

## Standard-Features

### B-1: Message-Editing
- [x] Edit-Banner, m.replace mit m.new_content, Escape-Cancel, (bearbeitet) Badge

### B-2: Read Receipts visuell
- [x] Mini-Avatare unter eigenen Nachrichten (max 5)
- [x] RoomEvent.Receipt Listener Fix

### B-3: Reactions
- [x] 8-Emoji Quick-Picker, m.reaction mit m.annotation
- [x] Click-Outside-to-Close Fix

### B-4: Nachrichten loeschen (Redaction)
- [x] Hover-Menue → Loeschen mit Confirm-Dialog
- [x] isRedacted Boolean statt String-Vergleich Fix

### B-5: URL-Vorschauen
- [x] OpenGraph-Vorschau via Next.js API Route
- [x] Multi-User Privacy Fix (eigener Token statt statischer)

### B-6: Presence / Online-Status
- [x] Gruener Punkt am Avatar fuer online User
- [x] Sliding Sync presence extension Fix

### B-7: Polls (MSC3381)
- [x] Abstimmungen erstellen, abstimmen, Ergebnisse live
- [x] usePoll.ts, PollMessage.tsx, CreatePollDialog.tsx

### B-8: Thread-Unterstuetzung (MSC3440)
- [x] Thread-Replies in Side-Panel
- [x] Thread-Chip auf Root-Nachrichten
- [x] useThreadTimeline.ts, ThreadPanel.tsx

### B-9: Voice/Video Calls (Legacy → MatrixRTC)
- [x] Legacy VoIP implementiert (exec-03)
- [x] Migriert zu MatrixRTC + LiveKit (exec-04/08)
- [x] E2EE via MatrixKeyProvider
- [x] 1:1 + Gruppen, Voice + Video, Screen Share

---

## Offene Punkte (Backlog)

### C-4: Encrypted State Events (MSC3414/MSC4362)
- [ ] Vorbereitet in SDK, wartet auf Tuwunel-Support
- [ ] Aktivierung: `enableEncryptedStateEvents: true`

### C-6b: Gruppen-Calls Blueprint
- [x] Architektur dokumentiert in exec-03
- [x] Implementiert in exec-04/08 (LiveKit + MatrixRTC)
