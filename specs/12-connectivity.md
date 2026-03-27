# Connectivity — Tunnel, VPS, IPv6, Production-Erreichbarkeit

## Übersicht

Dieses Dokument beschreibt alle Optionen um den Matrix-Homeserver von außen
erreichbar zu machen — für Mobile-Tests, für Freunde und für Production.

---

## Das Problem

Tuwunel läuft auf `127.0.0.1:8448` — nur lokal erreichbar.
Handys, Freunde und Element X brauchen eine öffentliche Adresse.

```
Handy ──?──► ??? ──► 127.0.0.1:8448 (Tuwunel, dein PC)
```

**Lösung:** Entweder Tuwunel direkt erreichbar machen (IPv6/Port-Forward)
oder einen Tunnel dazwischenschalten.

---

## Option 1 — Cloudflare Tunnel (Empfohlen für Production ohne VPS)

### Quick Tunnel (kein Account, für Dev-Tests)
```powershell
tools/cloudflared.exe tunnel --url http://localhost:8448
# → https://xxxx.trycloudflare.com  (temporär, ändert sich bei Neustart)
```

### Dauerhafter Tunnel mit eigener Domain (kostenlos, für Production)

Voraussetzung: eigene Domain auf Cloudflare (z.B. matrix.deine-domain.com)

```bash
# 1. cloudflared Account erstellen (kostenlos)
tools/cloudflared.exe login

# 2. Tunnel erstellen
tools/cloudflared.exe tunnel create matrix-tunnel

# 3. Config erstellen (~/.cloudflared/config.yml)
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: matrix.deine-domain.com
    service: http://localhost:8448
  - service: http_status:404

# 4. DNS-Eintrag erstellen
tools/cloudflared.exe tunnel route dns matrix-tunnel matrix.deine-domain.com

# 5. Tunnel starten
tools/cloudflared.exe tunnel run matrix-tunnel
```

**Ergebnis:** `https://matrix.deine-domain.com` → dein Tuwunel
- HTTPS automatisch (Let's Encrypt via Cloudflare)
- Stabile URL, ändert sich nie
- Komplett kostenlos (Cloudflare Free Plan)
- Kein VPS nötig

---

## Option 2 — IPv6 direkt (kein Tunnel, kein Drittanbieter)

### Warum IPv6 hier funktioniert

IPv4: Router hat eine IP, alle Geräte dahinter teilen sich diese via NAT.
IPv6: Jedes Gerät bekommt eine eigene öffentliche IP — kein NAT nötig.

```
IPv4: Handy → Router-IP (NAT) → PC  ← braucht Port-Forward oder Tunnel
IPv6: Handy → PC-IPv6-Adresse       ← direkte Verbindung möglich
```

Die meisten modernen ISPs (Telekom, Vodafone, O2) vergeben IPv6-Adressen.

### Setup

```powershell
# 1. Deine IPv6-Adresse herausfinden
ipconfig | findstr "IPv6"
# → z.B. 2003:de:373e:4500:xxxx:xxxx:xxxx:xxxx

# 2. tuwunel.toml anpassen
# address = "0.0.0.0"  # hört auf alle Interfaces inkl. IPv6

# 3. Windows Firewall: Port 8448 für IPv6 freigeben
netsh advfirewall firewall add rule name="Tuwunel IPv6" protocol=TCP dir=in localport=8448 action=allow

# 4. Router-Firewall: IPv6-Port 8448 freigeben
# (Fritzbox: Heimnetz → Netzwerk → IPv6 → Firewall → Port 8448 für deinen PC)
```

```
# In Element X eingeben:
http://[2003:de:373e:4500:xxxx:xxxx:xxxx:xxxx]:8448
```

### Problem: IPv6-Adresse ändert sich

ISPs verwenden Privacy Extensions — die IPv6-Adresse ändert sich regelmäßig.

**Lösung: DynDNS für IPv6**
```powershell
# dynv6.com (kostenlos): gibt dir matrix.dynv6.net
# Update-Script (PowerShell, als Scheduled Task):
$ip = (Get-NetIPAddress -AddressFamily IPv6 -PrefixOrigin RouterAdvertisement |
       Where-Object { $_.IPAddress -notlike "fe80*" } |
       Select-Object -First 1).IPAddress
Invoke-WebRequest "https://dynv6.com/api/update?hostname=matrix.dynv6.net&token=DEIN_TOKEN&ipv6=$ip"
```

**Ergebnis:** `http://matrix.dynv6.net:8448` → dein Tuwunel
- Kein VPS, kein Tunnel, kein Drittanbieter
- Kein HTTPS (Element X zeigt Warnung) → Caddy/Nginx lokal für TLS nötig

---

## Option 3 — Port-Forward + DynDNS (IPv4)

Wenn ISP kein IPv6 gibt oder IPv4 einfacher ist.

```
Handy → deinname.duckdns.org → Router-IPv4 → Fritzbox → PC:8448
```

### Setup

```
# 1. duckdns.org: kostenloses Konto, Domain wählen (z.B. matrix-dev.duckdns.org)
# 2. Fritzbox: Heimnetz → Netzwerk → DynDNS → duckdns.org eintragen
# 3. Fritzbox: Internet → Freigaben → Port 8448 TCP → dein PC
# 4. tuwunel.toml: address = "0.0.0.0"
```

**Einschränkung:** Manche ISPs blockieren eingehende Verbindungen (Carrier-Grade NAT).
Dann funktioniert das nicht → IPv6 oder Cloudflare Tunnel nutzen.

---

## Option 4 — Tailscale (Für Testgruppe ohne öffentliches Internet)

Tailscale erstellt ein privates Mesh-VPN. Alle Teilnehmer bekommen eine stabile
`100.x.x.x` IP die sich nie ändert.

```
Du (PC)    → Tailscale-IP: 100.64.1.1
Freund A   → Tailscale-IP: 100.64.1.2
Freund B   → Tailscale-IP: 100.64.1.3
Handy      → Tailscale-IP: 100.64.1.4
```

```
# Element X: http://100.64.1.1:8448
# Kein öffentliches Internet, HTTP reicht
# Freunde müssen Tailscale installieren
```

**Ideal für:** kleinen geschlossenen Testkreis (5-10 Personen), kein öffentlicher Zugang.
**Nicht ideal für:** öffentliche Registrierung, unbekannte User.

---

## Option 5 — Eigener Server (wenn vorhanden)

Wenn bereits ein Server mit öffentlicher IPv4 vorhanden ist (kein neuer VPS nötig):

```
Tuwunel läuft direkt auf dem Server:
server.deine-domain.com:8448 → Tuwunel (direkt, kein Tunnel)

Nginx als Reverse Proxy davor:
matrix.deine-domain.com (HTTPS) → Nginx → localhost:8448
```

```nginx
server {
    listen 443 ssl;
    server_name matrix.deine-domain.com;

    ssl_certificate     /etc/letsencrypt/live/matrix.deine-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/matrix.deine-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8448;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Tuwunel auf dem Server bleibt auf `127.0.0.1` (nur Nginx hat Zugriff).

---

## Option 6 — bore (Open Source Tunnel)

Siehe `specs/11-bore-tunnel.md` für Details.

```powershell
# Schnelltest (kein Account, kein HTTPS)
tools/bore.exe local 8448 --to bore.pub
# → bore.pub:XXXXX
```

---

## Entscheidungsbaum

```
Willst du testen?
├── Nur du selbst (lokal)
│   └── 127.0.0.1 reicht — kein Tunnel nötig
│
├── Mit Handy (kurzer Test heute)
│   └── cloudflared Quick Tunnel → https://xxxx.trycloudflare.com
│
├── Mit Freunden (Testgruppe, geschlossen)
│   └── Tailscale → stabile IPs, kein Internet nötig
│
└── Production / öffentlich
    ├── Eigener Server vorhanden?
    │   └── Tuwunel direkt + Nginx + Let's Encrypt
    ├── Domain auf Cloudflare?
    │   └── Cloudflare Tunnel (kostenlos, stabil)
    ├── ISP gibt IPv6?
    │   └── IPv6 + dynv6.com DynDNS
    └── Fritzbox + IPv4?
        └── Port-Forward + duckdns.org
```

---

## VPS — wann wirklich nötig?

| Use Case | VPS nötig? | Alternative |
|---|---|---|
| Local Dev + Handy testen | ❌ | cloudflared Quick Tunnel |
| Freunde einladen (Testgruppe) | ❌ | Tailscale |
| Production mit eigenem Domain | ❌ | Cloudflare Tunnel (kostenlos) |
| Production mit IPv6 | ❌ | IPv6 direkt + DynDNS |
| Eigener bore Relay Server | ✅ | bore.pub (Drittanbieter) |
| Eigener Mail-Server | ✅ | Kein guter Workaround (Spam-Problem) |
| 24/7 Verfügbarkeit ohne PC anlassen | ✅ | Raspberry Pi (einmalig ~60€) |

**Fazit:** Für Matrix-Homeserver brauchst du keinen VPS solange du eine Domain
auf Cloudflare hast oder IPv6 nutzt. Ein VPS wird erst nötig wenn der PC
nicht 24/7 laufen soll oder du vollständige Server-Kontrolle willst.

---

## IPv6 vs. IPv4 — Kurzerklärung

```
IPv4: 192.168.1.1          → 4 Milliarden Adressen (fast aufgebraucht)
IPv6: 2003:de:373e:4500::1 → 340 Sextillionen Adressen (genug für alles)
```

IPv4 brauchte NAT (Router übersetzt eine öffentliche IP auf viele private).
IPv6 hat genug Adressen für jedes Gerät eine eigene öffentliche IP zu geben.

**Spam-Problem bei eigenem Mail-Server:**
IP-Reputation wird von großen Anbietern (Gmail, Outlook) bewertet.
Neue IPs (VPS, Home-IP) haben keine Reputation → Spam-Ordner.
IPv6-Adressen haben dasselbe Problem — die Adresse ist unbekannt.
Lösung: Reverse DNS, SPF, DKIM, DMARC korrekt konfigurieren — aufwändig.
Deshalb nutzen viele Firmen Relay-Services (SendGrid, Mailgun) statt eigenem Server.

---

## Für unser Projekt — Empfohlener Weg

### Dev (jetzt):
```powershell
.\scripts\devstack.ps1 -Tunnel   # cloudflared → ngrok → bore
```

### Testing mit Freunden:
- Alle installieren Tailscale → stabile IPs, kein Setup pro Session

### Production (später):
- Domain auf Cloudflare registrieren (~10€/Jahr für .com)
- Cloudflare Tunnel einrichten (kostenlos)
- `tuwunel.toml`: `server_name = "matrix.deine-domain.com"`
- Registration deaktivieren, User via Admin-API erstellen

---

## TURN Server (Voice/Video Calls — Production)

### Warum TURN?

STUN reicht nur wenn mindestens ein Peer eine direkte Verbindung herstellen kann.
Wenn beide hinter striktem NAT sitzen (typisch bei Mobilfunk), braucht man TURN
als Relay — der Server leitet dann Audio/Video zwischen den Peers weiter.

```
STUN:  Peer A ←──────────────────→ Peer B     (direkt, wenn NAT es erlaubt)
TURN:  Peer A ←→ TURN-Server ←→ Peer B        (Relay, funktioniert immer)
```

### Dev: Nur STUN (jetzt aktiv)

In `tuwunel.toml` sind öffentliche STUN-Server konfiguriert:
```toml
turn_uris = ["stun:stun.cloudflare.com:3478", "stun:stun.l.google.com:19302"]
```
Reicht für Calls im LAN und einfaches NAT. Kein eigener Server nötig.

### Production: coturn

coturn ist der Standard-TURN-Server für Matrix. Braucht einen Server mit öffentlicher IP.

```bash
# 1. coturn installieren (auf VPS oder eigenem Server)
sudo apt install coturn

# 2. /etc/turnserver.conf
listening-port=3478
tls-listening-port=5349
realm=matrix.deine-domain.com
use-auth-secret
static-auth-secret=GENERIERTES_SECRET
cert=/etc/letsencrypt/live/matrix.deine-domain.com/fullchain.pem
pkey=/etc/letsencrypt/live/matrix.deine-domain.com/privkey.pem
no-multicast-peers
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255

# 3. tuwunel.toml (Production)
turn_uris = ["turn:turn.deine-domain.com?transport=udp", "turn:turn.deine-domain.com?transport=tcp"]
turn_secret = "GENERIERTES_SECRET"
turn_ttl = 86400
```

### Alternative: Cloudflare TURN (Managed)

Cloudflare bietet einen managed TURN-Service. Kein eigener Server nötig,
aber kostenpflichtig nach Free Tier (1 GB/Monat kostenlos).

### Entscheidung

| Szenario | STUN reicht? | TURN nötig? |
|---|---|---|
| Calls im LAN | ✅ | ❌ |
| Calls über WLAN (gleiches NAT) | ✅ | ❌ |
| Calls Mobilfunk ↔ WLAN | ❌ | ✅ |
| Calls Mobilfunk ↔ Mobilfunk | ❌ | ✅ |
