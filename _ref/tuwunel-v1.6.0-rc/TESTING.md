# Tuwunel v1.6.0-rc — Testing Runbook

**Stand:** 2026-04-11
**Binary:** `tools/tuwunel-v1.6` (v1.6.0 — RC status)
**Config:** `homeserver/tuwunel.v1.6.toml`
**Setup-Modus:** Shared DB mit v1.5.1 (`./homeserver/data/db`) + Pre-flight-Backup

---

## Schritt 0 — Vor dem allerersten Start

### Backup erstellen

**Der einzige Weg zurück zu v1.5.1 nach einem Schema-Upgrade ist dieses Backup.** Nicht überspringen.

```powershell
# Wenn Tuwunel aktuell laeuft → devstack schliessen (Ctrl+C / Fenster zu)
.\scripts\backup-before-v1.6.ps1
```

Das Skript kopiert:
- `homeserver/data/db` → `homeserver/data/db-pre-v1.6`
- `homeserver/data/media` → `homeserver/data/media-pre-v1.6`

Dauer: ~5–10 Sekunden bei kleiner Dev-DB. Refused wenn Port 8448 noch gebunden ist.

### SeaweedFS-Bucket prüfen/erstellen

Tuwunel v1.6.0 will beim Startup den S3-Bucket `matrix-media` erreichen können. SeaweedFS legt Buckets on-the-fly an wenn `use_bucket_key = false` und Credentials Admin-Rechte haben (beides der Fall).

**Falls der Startup-Check fehlschlägt:** manuell erzeugen via SeaweedFS Filer UI (http://localhost:8888) oder via S3 CLI. Wir lassen das erstmal auf implizit-erzeugen laufen.

---

## Phase 1 — Smoke-Test ohne S3

Ziel: **"Läuft v1.6.0-rc überhaupt sauber?"**

**Config-State:** `store_media_on_providers = ["media"]` (= lokaler Filesystem-Provider, wie bei v1.5.1)

```powershell
.\scripts\dev-stack2.ps1 -Tuwunel16
```

**Erwartetes Verhalten:**
- Gelbe Zeile beim Startup: `[tuwunel] Using v1.6.0-rc (...)`
- Tuwunel startet in ~5–10 Sekunden (erster Start kann länger dauern wegen Schema-Migration — bis zu 30s ist normal, länger verdächtig)
- Kein Crash, kein Panic
- `http://localhost:8448/_matrix/client/versions` antwortet mit `{"versions": [...]}`
- Logs in `logs/dev-stack/tuwunel.stderr.log` zeigen `Server started on ...`

**Test:**
1. Element X öffnen, Login zum bestehenden Account (matrix.local)
   - ⚠️ Falls "Invalid Access Token" → **erwartet nach DB-Migration**, einmal neu einloggen
2. Einen bestehenden Raum öffnen → Historie muss sichtbar sein
3. Neue Textnachricht posten → erscheint sofort
4. Bild posten (< 100 MB) → wird hochgeladen und angezeigt

**Abbruch-Kriterien:**
- Tuwunel crasht beim Start → **Rollback zu v1.5.1**
- Alte Rooms sind leer oder fehlen → **Rollback**
- Element X kann keine Nachrichten mehr lesen → **Rollback**

### Wie Rollback geht

```powershell
# 1. Devstack schliessen
# 2. DB zurueck
Remove-Item -Recurse -Force homeserver/data/db
Copy-Item -Recurse homeserver/data/db-pre-v1.6 homeserver/data/db
# 3. Media zurueck
Remove-Item -Recurse -Force homeserver/data/media
Copy-Item -Recurse homeserver/data/media-pre-v1.6 homeserver/data/media
# 4. devstack ohne -Tuwunel16 neu starten
.\scripts\dev-stack2.ps1
```

---

## Phase 2 — S3 Storage Provider aktivieren

Ziel: **"Schreibt Tuwunel neue Media in SeaweedFS statt ins Filesystem?"**

**Voraussetzung:** Phase 1 war erfolgreich. Devstack läuft.

**Config-Änderung:** In `homeserver/tuwunel.v1.6.toml`:

```toml
# vorher:
store_media_on_providers = ["media"]
# nachher:
store_media_on_providers = ["seaweedfs"]
```

Danach devstack neu starten (`-Tuwunel16` weiterhin gesetzt).

**Test:**
1. Ein neues Bild in einem Raum posten (Element X oder Web)
2. SeaweedFS Filer UI öffnen: http://localhost:8888
3. Browse zum Pfad `matrix-media/tuwunel-v1.6/` (oder `buckets/matrix-media/tuwunel-v1.6/`)
4. Die hochgeladene Datei sollte dort als Blob sichtbar sein
5. In Element X das Bild erneut öffnen → Download funktioniert (= Tuwunel liest aus S3)
6. Altes Bild (aus Phase 1 oder früher) erneut öffnen → Download funktioniert (= Tuwunel liest aus local fallback `media`)

**Abbruch-Kriterien:**
- Upload schlägt mit 5xx fehl → Log checken (`logs/dev-stack/tuwunel.stderr.log`), S3-Credentials/Endpoint verifizieren
- Upload geht durch aber Blob nicht in SeaweedFS sichtbar → `base_path` / `endpoint` in Config prüfen
- Alte Bilder sind plötzlich unreachable → `media_storage_providers` muss `["media", "seaweedfs"]` in dieser Reihenfolge haben

---

## Phase 3 — MSC2246 Async Upload testen

Ziel: **"Nutzt Element X den neuen entkoppelten Upload-Flow?"**

**Voraussetzung:** Phase 2 erfolgreich (S3 aktiv).

**Test:**
1. Element X Version prüfen: mindestens v0.8+ für MSC2246-Support
2. Großes Bild (~50 MB) posten
3. In `logs/dev-stack/tuwunel.stderr.log` nach Requests suchen:
   ```
   POST /_matrix/media/v1/create
   PUT  /_matrix/media/v3/upload/matrix.local/<mediaId>
   ```
   Wenn beides als getrennte Requests auftaucht → **MSC2246 aktiv**
   Wenn nur `POST /_matrix/media/v3/upload` → Client nutzt Legacy-Flow (trotzdem ok, aber kein Resume-Support)

**Keine Abbruch-Kriterien** — beide Pfade sind valide, wir prüfen nur was Element X gerade benutzt.

---

## Phase 4 — `max_request_size` hochsetzen (optional)

Ziel: **"Können wir >100 MB Uploads durchbekommen, wenn wir den Cloudflare-Tunnel umgehen?"**

**Nur lokaler Test** — funktioniert NICHT wenn Element X über Cloudflare-Tunnel verbunden ist (CF capped bei 100 MB unabhängig vom Tuwunel-Limit).

**Config-Änderung:**
```toml
max_request_size = 524288000  # 500 MB
```

Devstack neu starten.

**Test:**
1. Element X im selben LAN → direkt `http://192.168.1.34:8448` (kein Cloudflare dazwischen)
2. Video oder große Datei ~200 MB posten
3. Upload sollte durchgehen
4. Im SeaweedFS-Bucket als Blob sichtbar

**Falls Interesse:** Testen ob MSC2246 async upload auf große Files resumable wirkt — dafür während Upload die Client-Verbindung kappen und schauen ob Element X weitermacht.

---

## Phase 5 — Merge-Entscheidung

Nach mindestens 3 Tagen v1.6.0-rc Betrieb ohne Regression:

### Option A: Warten auf stable
- v1.6.0 stable erwartet Ende April / Anfang Mai 2026
- Dann `tools/tuwunel-v1.6` durch stable Binary ersetzen
- `tuwunel.toml` und `tuwunel.v1.6.toml` konsolidieren
- `-Tuwunel16` Flag aus `dev-stack2.ps1` entfernen

### Option B: RC direkt produktiv nutzen
- Nur wenn RC völlig stabil läuft und Storage-Provider + MSC2246 funktionieren
- `tools/tuwunel` durch v1.6 Binary ersetzen
- Alte `tuwunel.toml` durch `tuwunel.v1.6.toml` ersetzen
- Backup-Verzeichnisse `db-pre-v1.6` / `media-pre-v1.6` behalten als Safety-Net bis stable draußen ist

---

## Troubleshooting-Checkliste

| Symptom | Wahrscheinliche Ursache | Fix |
|---|---|---|
| Binary läuft nicht in WSL | chmod +x fehlt | `wsl chmod +x /mnt/d/matrix/tools/tuwunel-v1.6` |
| "failed to open database" | Lockfile von altem Prozess | In WSL: `rm homeserver/data/db/LOCK` (nur wenn sicher kein Prozess läuft!) |
| S3 startup check fails | SeaweedFS nicht gestartet | Devstack hat `seaweedfs` in der Service-Liste; beim nächsten Start warten bis Tier-1 (infra) hochgefahren ist |
| "No such bucket: matrix-media" | Bucket nicht angelegt | Manuell via `weed shell` oder SeaweedFS Filer UI erstellen |
| Element X "Server unreachable" | `well_known` IP falsch | In `tuwunel.v1.6.toml` die `client = "http://192.168.1.34:8448"` LAN-IP prüfen |
| Upload 413 Payload Too Large | CF-Tunnel aktiv + große Datei | Entweder CF-Tunnel deaktivieren oder Datei < 100 MB halten |
| v1.6 startet, aber alte Chat-History weg | Schema-Migration hat was verändert | **Sofort Rollback**, GitHub-Issue erwägen |
