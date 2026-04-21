# exec-linux-setup-users — Matrix User-Setup auf Linux

**Datum**: 2026-04-17
**Status**: ✅ Script ready, muss manuell ausgeführt werden nach Tuwunel-Start

## Motivation

Die Windows-Variante (`scripts/setup-users.ps1`) lief auf Windows gegen tuwunel v1.5 in WSL. Nach Migration auf Linux Mint ist:
- DB (`homeserver/data/`) **weg** (lag auf Windows-drive)
- PowerShell-Script funktioniert nicht unter bash
- alice + andere User **müssen neu erstellt werden**

## Approach

**`scripts/setup-users.sh`** — Linux-bash-Port mit gleichen Features:
- Registriert alice, bob, agent-bot via Matrix Registration API
- Nutzt `registration_token = "matrix-dev-token-2026"` aus tuwunel.v1.6.toml
- Schreibt `access_token` + `device_id` + `user_id` in die jeweiligen `.env` Files
- Idempotent: bei re-run → Login statt Register (preserve existing users)

## Usage

```bash
# 1. Tuwunel starten:
cd ~/code/matrix
podman-compose up -d tuwunel postgres

# 2. Warten bis tuwunel ready (ca. 10s):
curl -sf http://localhost:8448/_matrix/client/versions

# 3. Users erstellen:
./scripts/setup-users.sh
```

Output (erwartet):
```
==> Prüfe Tuwunel (http://localhost:8448)...
    OK: Tuwunel antwortet
==> Setup user @alice
    OK: @alice: access_token=syt_YWxpY2U_… device=ABCDEFGHIJ
    → frontend_merger/.env.local aktualisiert
==> Setup user @bob
    OK: @bob: access_token=syt_Ym9iXw… device=XYZABC
==> Setup user @agent-bot
    OK: @agent-bot: access_token=syt_… device=BOTDEV
    → python-backend/.env.development aktualisiert
```

## User-Struktur

| User | Purpose | Token geht in |
|---|---|---|
| `@alice:matrix.local` | Test-User Browser/Element-X, optional für frontend_merger SSR | `frontend_merger/.env.local` → `MATRIX_ACCESS_TOKEN`, `MATRIX_DEVICE_ID`, `MATRIX_USER_ID` |
| `@bob:matrix.local` | Zweiter Test-User für 2-User-Chat-Tests | (keine env-write) |
| `@agent-bot:matrix.local` | Python agent bot — postet Messages als Bot | `python-backend/.env.development` → `MATRIX_BOT_ACCESS_TOKEN`, `MATRIX_BOT_DEVICE_ID`, `MATRIX_BOT_USER_ID` |

**Nicht erstellt** (werden dynamisch vom Appservice erzeugt via AS-Pattern):
- `@appservice-bot` — Bridge-identity für go-appservice (registration.yaml sender_localpart)
- `@agent-trading`, `@agent-research`, ... — virtuelle Bot-User via `MATRIX_AGENT_PREFIX=agent-`

## Passwords

Aus `scripts/setup-users.sh`:
- `alice`: `alice-dev-password-2026` (hardcoded für Dev-convenience)
- `bob`: `bob-dev-password-2026` (hardcoded)
- `agent-bot`: aus `python-backend/.env.development` → `MATRIX_BOT_PASSWORD` (generated via bootstrap-env.py)

**In Prod**: Passwords rotieren + in SOPS-encrypted master ablegen. Für Dev sind hardcoded values OK.

## Verify Gates

- [ ] Tuwunel läuft (`curl http://localhost:8448/_matrix/client/versions` → 200)
- [ ] Script läuft ohne Fehler
- [ ] `@alice:matrix.local` erstellt (check via `/login` endpoint)
- [ ] `frontend_merger/.env.local` hat `MATRIX_ACCESS_TOKEN=syt_...` non-empty
- [ ] `python-backend/.env.development` hat `MATRIX_BOT_ACCESS_TOKEN=syt_...` non-empty
- [ ] Re-run idempotent (zweiter Lauf gibt gleiche tokens zurück)

## Troubleshooting

**"Register failed"** → User existiert schon (idempotent → Login wird versucht).

**"Login failed"** → Password mismatch. Check `MATRIX_BOT_PASSWORD` in `python-backend/.env.development` vs. initial bot-password.

**"Tuwunel nicht erreichbar"** → `podman-compose up -d tuwunel` und 10s warten.

**Registration-Token mismatch** → `homeserver/tuwunel.v1.6.toml` → `registration_token = "..."`. Das Script nimmt `matrix-dev-token-2026` als default.

## Post-Setup

### Element-X Login (mobile):
1. App installieren
2. Server: `http://localhost:8448` (oder `https://xxxx.trycloudflare.com` wenn tunnel aktiv)
3. Login mit `@alice` / `alice-dev-password-2026`

### Manueller Token-Check:
```bash
curl -s -H "Authorization: Bearer $(grep '^MATRIX_ACCESS_TOKEN=' frontend_merger/.env.local | cut -d= -f2)" \
  http://localhost:8448/_matrix/client/v3/account/whoami
# → {"user_id":"@alice:matrix.local","device_id":"ABCDEFGHIJ","is_guest":false}
```

## Related

- `homeserver/tuwunel.v1.6.toml` — `registration_token` value source
- `homeserver/registration.yaml` — Appservice-registration (AS/HS tokens, separate flow)
- `docs/env-vars.md` — Alle env-var mapping
- `scripts/setup-users.ps1` — Windows-Original (not used on Linux)
