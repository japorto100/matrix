# Mobile — Element X, FluffyChat, Syphon, Beeper

## App-Auswahl (Stand März 2026)

Alle vier Apps können: DMs, Gruppen-Räume, Bot als normaler Kontakt, E2EE.
Kein Custom APK nötig — offizielle Apps + Custom Homeserver URL eintragen.

| | Element X | FluffyChat | Syphon | Beeper |
|---|---|---|---|---|
| iOS | ✅ (iOS 18+) | ✅ | ✅ | ⚠️ WIP |
| Android | ✅ | ✅ | ✅ | ✅ |
| F-Droid / APK | ✅ | ✅ (GitHub Releases) | ✅ | ❌ |
| Rust SDK | ✅ (matrix-rust-sdk) | ❌ (Dart/Flutter) | ❌ | ❌ |
| Push Notifications | ✅ via Elements Sygnal | ✅ via Elements Sygnal | ✅ | ✅ |
| E2EE | ✅ | ✅ | ✅ | ✅ |
| Bot-Kontakte | ✅ | ✅ | ✅ | ✅ |
| Gruppen-Räume | ✅ | ✅ | ✅ | ✅ |
| Besonderheit | Schnellste Sync (Sliding Sync) | Einfachste UX | Privacy-first | Bridges zu WA/TG/Signal |

### Element X
- Offizielle App von Element HQ (matrix.org-Firma)
- Rust SDK → sehr performant
- Version 26.03.3 (März 2026)
- Play Store: `io.element.android.x` | App Store: `id1631335820`

### FluffyChat
- Community-Projekt, Nonprofit, Open Source (Dart/Flutter)
- Einfachste UX — am zugänglichsten für Nicht-Techniker
- APK direkt von GitHub: https://github.com/krille-chan/fluffychat/releases
- Version 2.4.0 (Januar 2026)

### Syphon
- Privacy-first Design, Signal-ähnliches UI
- Gut für datenschutzbewusste User
- iOS + Android

### Beeper
- Verbindet WhatsApp, Telegram, Signal, Discord via Matrix-Bridges
- Wenn User bereits WA/TG nutzen → ein Posteingang für alles
- Android vollständig, iOS noch in Entwicklung (März 2026)

---

## Push Notifications — Kein eigener Setup nötig

Offizielle Apps aus Play Store / App Store nutzen Elements Sygnal automatisch:

```
Tuwunel Homeserver → Elements Sygnal → Apple APNs / Google FCM → App
```

Kein eigenes APNs-Zertifikat, kein FCM-Projekt nötig.
Gilt für alle vier Apps wenn aus offiziellen Stores installiert.

**Eigener Sygnal erst nötig wenn:** Custom-branded App im eigenen Store, oder Sygnal-Kontrolle gewünscht.

---

## Mobile erreicht den Homeserver — Tunnel-Optionen

**Wichtig:** `tuwunel.toml` muss auf `address = "0.0.0.0"` geändert werden (aktuell `127.0.0.1`).

### Option A — Cloudflare Tunnel (Empfohlen für ersten Test)
```powershell
# Kein Konto nötig, sofort, HTTPS
tools/cloudflared.exe tunnel --url http://localhost:8448
# → https://xxxx.trycloudflare.com  ← in Element X eingeben
```
- Zufällige URL, ändert sich bei Neustart
- HTTPS automatisch → Element X ohne Warnungen

### Option B — bore (Open Source, kein Account)
```powershell
# bore.pub ist der öffentliche Relay-Server
tools/bore.exe local 8448 --to bore.pub
# → Gibt URL aus: bore.pub:XXXXX (TCP, kein HTTPS)
```
- Kein Account, komplett Open Source
- Kein HTTPS → Element X zeigt Warnung, FluffyChat akzeptiert HTTP
- Für HTTPS: eigene bore-Instanz mit Reverse Proxy

### Option C — ngrok (bekannteste Option, Account nötig)
```powershell
# Einmalig: Account erstellen → authtoken holen
tools/ngrok.exe config add-authtoken DEIN_TOKEN
# Dann:
tools/ngrok.exe http 8448
# → https://xxxx.ngrok-free.app  ← in Element X eingeben
```
- Account nötig (kostenlos, 1 Tunnel gleichzeitig)
- HTTPS automatisch
- Permanente Subdomain mit bezahltem Plan

### Option D — Tailscale (Beste für dauerhaftes Testing)
```
1. tailscale.com/download → Windows App installieren
2. Tailscale App auf Handy installieren → gleicher Account
3. tuwunel.toml: address = "0.0.0.0"
4. Element X: http://100.64.x.x:8448  (Tailscale-IP, immer gleich)
```
- Mesh-VPN: Handy und PC im selben virtuellen Netz
- Kein öffentliches Internet, HTTP reicht
- Stabile IP (ändert sich nicht)
- Keine Tunneling-App nötig wenn testen

### Option E — Lokales WLAN (einfachste, nur zuhause)
```toml
# tuwunel.toml:
address = "0.0.0.0"
```
```
# Handy + PC im gleichen WLAN
# Element X: http://192.168.1.XXX:8448
```
- Kein Internet nötig
- HTTP → Warnung in Element X
- FluffyChat akzeptiert HTTP ohne Probleme

### Option F — Rathole (Self-Hosted Tunnel)
- Client-Server-Architektur: eigener Server nötig (VPS)
- Gut wenn eigener Produktions-Server bereits vorhanden
- https://github.com/rapiz1/rathole
- Für lokales Testing überdimensioniert

---

## Login in Element X / FluffyChat

```
1. App öffnen
2. "Andere Server" / "Custom Homeserver" wählen
3. URL eingeben: https://xxxx.trycloudflare.com  (oder lokale IP)
4. Username: alice   Passwort: Alice1234!
5. Bot-DM: @trading-agent:matrix.local
```

**Hinweis:** `server_name = "matrix.local"` ist nur ein Label in User-IDs,
kein DNS-Lookup. Die App verbindet sich zur eingegebenen URL, nicht zu matrix.local.

---

## tuwunel.toml für Mobile-Test

```toml
# Standardmäßig:
address = "127.0.0.1"   # nur localhost — Handy kann NICHT drauf zugreifen

# Für Mobile-Test ändern auf:
address = "0.0.0.0"     # alle Interfaces — Handy + Tunnel erreichbar
```

Nach Änderung Tuwunel neu starten.

---

## APK ohne Play Store (Android)

```powershell
# FluffyChat APK direkt von GitHub
# https://github.com/krille-chan/fluffychat/releases
# → fluffychat-release.apk herunterladen → per USB/ADB installieren

# Element X via F-Droid
# F-Droid installieren → "Element X" suchen → installieren
```

iOS: kein APK-Äquivalent ohne Apple Developer Account.
Für iOS-Freunde: App Store (Element X oder FluffyChat).

---

## SchildiChat Next (Element X Fork für Android)

- Fork von Element X mit zusätzlichen Features
- Android only
- https://schildi.chat/android/
- Alternative wenn Element X-Basis mit mehr Optionen gewünscht
