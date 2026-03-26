# Mobile-Test: Element X mit lokalem Homeserver

> Erstellt: 25.03.2026
> Ziel: Element X auf dem Handy verbindet sich mit Tuwunel im LAN

---

## Voraussetzungen

- Handy und PC im **gleichen WLAN**
- Element X installiert ([Android](https://play.google.com/store/apps/details?id=io.element.android.x) / [iOS](https://apps.apple.com/app/element-x-secure-messenger/id6448641239))
- PC LAN-IP: **192.168.1.34** (prüfen mit `ipconfig`)
- Firewall: Port 8448 TCP eingehend erlaubt ✅ (bereits eingerichtet)

---

## Dev-Credentials

| Was | Wert |
|---|---|
| Homeserver-URL (Handy) | `http://192.168.1.34:8448` |
| Homeserver-URL (Webapp) | `http://localhost:8448` |
| Username | `alice` |
| Password | `Alice1234!` |
| User-ID | `@alice:matrix.local` |
| Device-ID (Webapp) | `ALICE01` |
| Access Token (Webapp) | `bi7h8zYp9oc84vv1XZU6UsDWbPXYpD1K` |
| Registration Token | `matrix-dev-token-2026` |

---

## Schritt 1: Devstack starten

```powershell
cd D:\matrix
.\scripts\devstack.ps1
```

Oder manuell (einzelne Terminals):

```bash
# Terminal 1: Tuwunel (WSL)
wsl -d Ubuntu -u root bash -c "cd /mnt/d/matrix && ./tools/tuwunel --config ./homeserver/tuwunel.toml"

# Terminal 2: NATS
D:\matrix\tools\nats-server.exe

# Terminal 3: Go Appservice
cd D:\matrix\go-appservice && go run -tags goolm ./cmd/appservice/...

# Terminal 4: Next.js
cd D:\matrix\nextjs-chat && bun dev
```

**Warten bis alle Services laufen:**
- Tuwunel: `http://localhost:8448` erreichbar
- Next.js: `http://localhost:3000/matrix` zeigt Chat

---

## Schritt 2: Prüfen ob Tuwunel im LAN erreichbar ist

Vom Handy-Browser öffnen:

```
http://192.168.1.34:8448/_matrix/client/versions
```

**Erwartet:** JSON mit `versions` Array. Wenn Timeout → Firewall prüfen oder IP prüfen.

Falls IP sich geändert hat:
```powershell
# Auf dem PC:
ipconfig | findstr "IPv4"
```
→ Neue IP in `tuwunel.toml` bei `[global.well_known]` und in dieser Anleitung anpassen.

---

## Schritt 3: Element X — Login

1. **Element X** auf dem Handy öffnen
2. Auf **"Change server"** / **"Anderen Server verwenden"** tippen
3. Eingeben: **`http://192.168.1.34:8448`**
4. "Continue" / "Weiter"
5. **Username:** `alice`
6. **Password:** `Alice1234!`
7. "Sign in" / "Anmelden"

**Erwartet:** Element X ist eingeloggt. Raumliste erscheint.

---

## Schritt 4: Cross-Signing Verifikation (E2EE)

Nachdem Element X eingeloggt ist:

1. **Webapp** öffnen: `http://localhost:3000/matrix`
2. Oben sollte ein **gelbes Banner** erscheinen: "Neues Gerät erkannt — Verifizieren"
3. Auf **"Verifizieren"** klicken → QR-Code erscheint
4. In **Element X** → Sicherheits-Prompt sollte erscheinen (oder unter Einstellungen → Sicherheit → Verifikation)
5. **QR-Code scannen** mit Element X
6. Beide Geräte bestätigen → **Grünes Schild**

**Erwartet:**
- Webapp: Banner verschwindet
- Element X: Gerät als verifiziert markiert (grünes Schild)
- E2EE-Nachrichten fließen zwischen Webapp und Element X

---

## Schritt 5: Testen

### Nachricht senden
- In **Webapp** eine Nachricht schreiben → erscheint in **Element X**
- In **Element X** antworten → erscheint in **Webapp**

### Bot testen
- In Element X den Agent-Raum öffnen (z.B. mit @agent-trading:matrix.local)
- Nachricht senden → Bot antwortet

### Verschlüsselung prüfen
- In Element X: Raum-Info → "Verschlüsselung" → sollte "aktiv" zeigen
- Nachrichten sollten ein Schloss-Symbol haben

---

## Troubleshooting

| Problem | Lösung |
|---|---|
| Element X: "Server nicht erreichbar" | IP prüfen (`ipconfig`), Firewall prüfen, WLAN prüfen |
| Element X: "Unknown server" | URL exakt eingeben: `http://192.168.1.34:8448` (mit http://) |
| Webapp: Kein gelbes Banner | Browser-Console prüfen, ggf. Page Reload |
| Cross-Signing QR erscheint nicht | E2EE muss in beiden Clients aktiv sein |
| Bot antwortet nicht | Go Appservice + NATS + Python Bridge laufen? |
| IP hat sich geändert | `tuwunel.toml` → `[global.well_known]` → client/server anpassen, Tuwunel neu starten |

---

## Firewall-Regel (bereits eingerichtet)

```powershell
# Falls nötig nochmal manuell:
netsh advfirewall firewall add rule name="Tuwunel Matrix Homeserver" dir=in action=allow protocol=tcp localport=8448 profile=private

# Prüfen:
netsh advfirewall firewall show rule name="Tuwunel Matrix Homeserver"

# Entfernen:
netsh advfirewall firewall delete rule name="Tuwunel Matrix Homeserver"
```

---

## Nach dem Test

Die `address = "0.0.0.0"` in `tuwunel.toml` und die Firewall-Regel können bleiben für weitere LAN-Tests. Für rein lokale Entwicklung ohne Mobile kann man auf `127.0.0.1` zurückstellen.
