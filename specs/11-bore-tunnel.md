# bore — Open-Source Reverse Tunnel

## Was ist bore?

bore ist ein minimaler Reverse-Tunnel in Rust. Ein Befehl, kein Account, kein Setup.

```
tools/bore.exe local 8448 --to bore.pub
# → listening at bore.pub:34521
```

Jetzt kann jedes Gerät auf `http://bore.pub:34521` dein lokales Tuwunel erreichen.

---

## Wie funktioniert es technisch?

```
Handy ──HTTP──► bore.pub:34521
                     │
               bore Relay Server
                     │ (persistente TCP-Verbindung)
                     │
               bore.exe (läuft auf deinem PC)
                     │
               localhost:8448 (Tuwunel)
```

1. `bore.exe` baut beim Start eine ausgehende TCP-Verbindung zu `bore.pub`
2. bore.pub weist einen zufälligen Port zu (z.B. 34521)
3. Alle eingehenden Requests auf `bore.pub:34521` werden durch diese Verbindung zu dir geleitet
4. Tuwunel antwortet — Antwort geht den gleichen Weg zurück

**Wichtig:** bore tunnelt reines TCP — kein HTTPS. Der Browser/die App verbindet direkt mit deinem Tuwunel via HTTP.

---

## Vergleich mit Alternativen

| | bore | cloudflared | ngrok |
|---|---|---|---|
| HTTPS | ❌ (nur TCP) | ✅ automatisch | ✅ automatisch |
| Account | ❌ nicht nötig | ❌ nicht nötig (quick tunnel) | ✅ nötig |
| URL stabil | ❌ ändert sich | ❌ ändert sich | ✅ (paid) |
| Open Source | ✅ vollständig | ⚠️ teilweise | ❌ |
| Eigener Server | ✅ möglich | ❌ | ❌ |
| Element X Mobile | ❌ **Funktioniert nicht** (erzwingt HTTPS) | ✅ | ✅ |
| FluffyChat | ✅ (akzeptiert HTTP) | ✅ | ✅ |

> **Wichtig:** Element X (Android/iOS) akzeptiert **kein HTTP** — nur HTTPS.
> bore liefert nur TCP ohne TLS → Element X verweigert die Verbindung.
> Für Element X Mobile **muss** Cloudflare Tunnel oder ngrok verwendet werden.

---

## Eigener bore Relay Server — was bringt es?

### Vorteile gegenüber bore.pub

| | bore.pub | Eigener Server |
|---|---|---|
| Kontrolle | Fremder Server | Vollständige Kontrolle |
| HTTPS | ❌ | ✅ (mit Nginx/Caddy davor) |
| Stabile URL | ❌ (ändert sich) | ✅ (du wählst Port/Domain) |
| Traffic sichtbar | Theoretisch für bore.pub-Betreiber | Nur du |
| Kosten | Kostenlos | Server nötig |

### Wann sinnvoll?

Wenn du bereits einen Server mit öffentlicher IP hast (z.B. bestehender Produktionsserver),
kannst du bore dort laufen lassen — dann entfällt der Drittanbieter komplett.

```bash
# Auf deinem Server:
./bore server --secret mein-geheimes-passwort

# Auf deinem PC:
tools/bore.exe local 8448 --to dein-server.com --secret mein-geheimes-passwort
```

Mit Nginx auf dem Server + Let's Encrypt → HTTPS für bore-Verbindungen.

---

## Produktive Tunnel-Optionen (kein VPS nötig)

Für Production brauchst du keinen eigenen Tunnel-Server. Bessere Wege:

### Option 1 — Cloudflare Tunnel + eigene Domain (kostenlos)
```
deine-domain.com (auf Cloudflare) → Zero Trust Tunnel → Tuwunel
```
- Komplett kostenlos (Cloudflare Free Plan)
- HTTPS automatisch mit eigenem Domain-Namen
- Stabile URL
- Kein VPS nötig

### Option 2 — IPv6 direkt
```
Handy ──IPv6──► deine öffentliche IPv6-Adresse → Tuwunel :8448
```
- Die meisten modernen ISPs geben öffentliche IPv6-Adressen
- Kein Tunnel, kein Drittanbieter, komplett kostenlos
- Router-Firewall: Port 8448 für IPv6 freigeben
- DynDNS für IPv6: dynv6.com (kostenlos) gibt dir `deinname.dynv6.net`

### Option 3 — Fritzbox + DynDNS (IPv4)
```
deinname.duckdns.org → deine Router-IPv4 → Fritzbox Port-Forward → Tuwunel
```
- duckdns.org: kostenloser DynDNS
- Fritzbox aktualisiert DynDNS automatisch
- Port 8448 im Router weiterleiten
- Kein VPS, kein Drittanbieter

---

## Nutzung im devstack

```powershell
# Startet Stack + Tunnel (cloudflared → ngrok → bore als Fallback)
.\scripts\devstack.ps1 -Tunnel

# Tunnel alleine starten
tools/cloudflared.exe tunnel --url http://localhost:8448
tools/bore.exe local 8448 --to bore.pub
tools/ngrok.exe http 8448
```

**Voraussetzung:** `tuwunel.toml` muss `address = "0.0.0.0"` haben (nicht `127.0.0.1`).
