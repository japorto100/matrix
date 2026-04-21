# exec-matrix-monitor — passiv warten auf Upstream

**Zweck:** Matrix-specific Upstream-Watch-Liste. Items hier sind **nicht aktiv entwickelbar** — wir warten auf ein upstream-Release, einen Bugfix oder eine Protokoll-Implementation. Periodisch re-evaluieren.

**Unterschied zu `exec2-04-verify-gates.md`:** Dort stehen *aktive* Verify-Gates (wir testen jetzt). Hier stehen *passive* Monitor-Items (wir warten).

**Unterschied zu `exec-blocking.md`:** `exec-blocking.md` ist die globale Sammelstelle über alle Cluster; diese Datei ist der Matrix-spezifische Auszug + eigene Matrix-only-Items.

**Re-Check-Kadenz:** monatlich, plus bei jedem Tuwunel-Release.

---

## M1. Tuwunel v1.6 stable Merge-Entscheidung

- **Quelle:** `exec2-04-verify-gates.md §J6` (ursprünglich)
- **Aktuell:** v1.6.0-rc läuft produktiv im devstack, Phase 1 smoke-test PASS (11.04.2026)
- **Warten auf:** Tuwunel v1.6.0 **stable** Release (erwartet Ende April / Anfang Mai 2026)
- **Trigger zum Handeln:**
  - v1.6.0 stable released
  - Mindestens 3 Tage Betrieb ohne Regression nachgewiesen
- **Dann zu tun:**
  - [ ] Entscheidung dokumentieren: RC produktiv nutzen ODER auf stable upgraden
  - [ ] `tools/tuwunel` und `homeserver/tuwunel.toml` konsolidieren (RC + stable Konfigs mergen)
  - [ ] `-Tuwunel16` Flag aus `dev-stack2.ps1` + `--tuwunel16` aus `dev-stack.sh` entfernen
  - [ ] `homeserver/data/db-pre-v1.6` und `media-pre-v1.6` löschen (erst wenn stable stabil läuft)

---

## M2. Tuwunel v1.6 Upstream-Bugs

- **Quelle:** `exec-blocking.md §C5`, `exec2-04-verify-gates.md §J7` (ursprünglich)
- **Re-Check:** bei jedem Tuwunel patch/minor-Release

| Bug | Severity | Unser Workaround | Status | Unblocks |
|---|---|---|---|---|
| [#411](https://github.com/matrix-construct/tuwunel/issues/411) S3 Large File Timeout (180s hard) | CRITICAL | `max_request_size ≤ 100 MB` | Upstream offen | exec2-04 J5 (`max_request_size` erhöhen) |
| [#401](https://github.com/matrix-construct/tuwunel/issues/401) Appservice /whoami fehlt device_id | HIGH | Prüfen ob mautrix-go betroffen; ggf. device_id aus lokaler Config laden | Go-Appservice-Test gegen v1.6 ausstehend | E2EE-Handoff bei Restart |
| [#377](https://github.com/matrix-construct/tuwunel/issues/377) device_lists.changed fehlt in /sync | MEDIUM | `FetchKeys()` Workaround in `go-appservice/internal/crypto/machine.go:EnsureSession()` — proaktiv gesetzt 11.04.2026 | ✅ gefixt (unser workaround), upstream offen | — |
| [#372](https://github.com/matrix-construct/tuwunel/issues/372) /room_keys/version 500 statt 404 | LOW | Prüfen ob mautrix-go den 500 als "kein Backup" handled | Go-Appservice-Test gegen v1.6 ausstehend | Key-Backup-Bootstrap |

**Action bei upstream-fix eines Items:**
1. Upstream changelog lesen ob fix vollständig
2. Workaround rückbauen (Code-Änderung in spec dokumentieren)
3. Zeile hier austragen

---

## M3. Encrypted State Events (MSC3414/MSC4362)

- **Quelle:** `exec-blocking.md §C1`, `exec2-01-matrix-chat-core.md §C-4`
- **Status:** kein Homeserver implementiert MSC3414/MSC4362 (Stand 11.04.2026). SDK vorbereitet, `enableEncryptedStateEvents` flag wartet.
- **Warten auf:**
  - Tuwunel changelog bestätigt MSC3414/MSC4362 Support, ODER
  - Entscheidung es serverseitig zu emulieren (nur falls protokollkonform)
- **Verify-Gates bei Aktivierung (aus exec2-04):**
  - [ ] `enableEncryptedStateEvents: true` aktivierbar
  - [ ] Encrypted State Events funktionieren ohne Decrypt-Fehler in Client + Bot

---

## M4. OIDC / MAS Auth

- **Quelle:** `exec-blocking.md §C2`, `exec2-02-protocol-infra.md`
- **Status:** MAS aktuell inkompatibel mit Tuwunel; nur Legacy SSO evaluiert. Konkrete Zielarchitektur unklar.
- **Warten auf:**
  - MAS Support in Tuwunel, ODER
  - Klares Portierungsziel (anderer Homeserver / Proxy-Lösung)
- **Gates bei Aktivierung:** OIDC-Login-Flow stabil, Token-Refresh, Logout, Appservice-Auth sauber
- **Blockiert Downstream:** `exec2-03b` Phase-A1 (Account-Auto-Create via MAS) — siehe `exec-blocking.md §C6`

---

## M5. Federation + Prod-Security

- **Quelle:** `exec-blocking.md §C3`, `exec2-04-verify-gates.md` Sektion "Federation + Security"
- **Status:** Aktuell private-only Deployment. Keine echte Domain/DNS/TLS.
- **Warten auf:** Deployment-Entscheidung "federation on" vs. "private-only" + Prod-Domain
- **Gates bei Aktivierung (aus exec2-04):**
  - [ ] `allow_federation = true` (falls gewollt)
  - [ ] DNS `_matrix._tcp` SRV oder `.well-known/matrix/server`
  - [ ] HTTPS + echte Domain
  - [ ] Anti-Spam Bot (Draupnir/Mjolnir), ACLs, invite-policy, Directory hidden

---

## M6. MSC2246 Async Upload (Client-dependent)

- **Quelle:** `exec2-04-verify-gates.md §J4`
- **Status:** Server (Tuwunel v1.6) unterstützt es. Erfolgreicher Test braucht Client mit MSC2246-Support.
- **Warten auf:** Element X v0.8+ oder anderer Client mit MSC2246-Impl im Testsetup
- **Gates (bei verfügbarem Client):**
  - [ ] Großes Bild (~50 MB) posten
  - [ ] Logs zeigen getrennte Requests: `POST /_matrix/media/v1/create` + `PUT /_matrix/media/v3/upload/matrix.local/<mediaId>`
  - [ ] Fallback: Legacy-Pfad `POST /_matrix/media/v3/upload` (kein Abbruch, nur Info)

---

## Changelog

| Datum | Änderung |
|---|---|
| 2026-04-21 | Erstversion. Extrahiert aus `exec2-04 §J6 + §J7` (Tuwunel v1.6 upstream-tracking) und aggregiert Matrix-spezifische Upstream-Pointer aus `exec-blocking.md §C1/C2/C3/C5`. |
