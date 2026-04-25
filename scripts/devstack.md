# DevStack — Setup & Operation

Arbeitet mit `scripts/dev-stack.sh`, `setup-garage.sh`, `setup-users.sh`,
`register-appservice.sh`.

## TL;DR — Täglicher Start

```bash
./scripts/dev-stack.sh --matrix-chat
```

Alles bereits persistiert (garage-keys, alice/bob, appservice) — einfach hoch.

## Presets

| Preset | Enthält | Use-case |
|---|---|---|
| `--matrix-core` | tuwunel + nats + postgres + garage + go + bridge + agent + frontend | Text-chat, agent-mentions (graceful degrade ohne LLM) |
| `--matrix-chat` | `matrix-core` + litellm | Volle agent-inference via OpenRouter |
| `--matrix-full` | `matrix-chat` + calls (livekit + lk-jwt + coturn) | alle exec2-04 Gates außer Tunnel |
| `--matrix-mobile` | `matrix-full` + cloudflared tunnel | Mobile external access |
| `--matrix-mock` | `matrix-core` + llm-mock | UI-tests ohne API-keys |
| `--agent-dev` | nats + postgres + litellm + agent + bridge | Agent-dev ohne Matrix |
| `--memory-dev` | postgres + falkordb + agent | Memory-exec-work |

Individuelle flags kombinierbar: `--matrix-chat --tunnel`, `--matrix-core --skip=frontend`, etc.
Vollständige Liste: `./scripts/dev-stack.sh --help`.

## Erster Start (fresh checkout / nach kompletten DB-wipe)

Reihenfolge **einmalig** nötig — danach persistiert's:

### 1. Garage S3-Storage initialisieren

```bash
./scripts/setup-garage.sh
```

Startet garage-container, init cluster-layout, generiert S3-keys, erstellt
buckets `matrix-media` + `matrix-artifacts`, schreibt keys in
`homeserver/tuwunel.v1.6.toml` + `go-appservice/.env.development`.

**Persistiert in:** podman volume `matrix_garage-data` + `matrix_garage-meta`.
**Nochmal nötig wenn:** garage-volume gewiped (`podman volume rm matrix_garage-data matrix_garage-meta`).

### 2. Stack hochfahren (infra-only für user-setup)

```bash
./scripts/dev-stack.sh --tuwunel --nats --postgres --storage=garage --litellm
```

Wartet bis tuwunel auf :8448 antwortet.

### 3. Alice + Bob registrieren

```bash
./scripts/setup-users.sh
```

Legt `@alice:matrix.local` + `@bob:matrix.local` an (UIAA registration_token).
Alice-token wandert in `frontend_merger/.env.local` (dev-convenience login).
Alice ist **first-user-admin** (automatisch) — wichtig für appservice-registration.

**Persistiert in:** podman volume `matrix_tuwunel-data`.
**Nochmal nötig wenn:** tuwunel-DB gewiped.

### 4. Rest des stacks dazu

```bash
./scripts/dev-stack.sh --matrix-chat
```

Additiv. Startet go-appservice + agent + bridge + frontend.
**Automatisch:** dev-stack.sh checkt ob appservice-namespace works. Wenn nein
(`M_EXCLUSIVE`-response auf probe-PUT) → ruft `register-appservice.sh` auf,
registriert via `!admin appservices register` als alice im #admins-room.

## Warum Appservice-Registration via admin-command?

Tuwunel v1.6.0 stable hat einen **parsing-bug**: Die inline
`[global.appservice.trading-agent]`-section in `tuwunel.v1.6.toml` wird nur
**partial geladen** — `as_token` + `hs_token` kommen durch (whoami returnt
`@appservice-bot`), aber die `namespaces.users.regex` landet nicht in der
internen DB. Gleiches bei `appservice_dir` yaml-discovery (brand-new v1.6
feature, hat edge-case bugs).

**Symptom:** Jede Operation auf `@agent-<name>` → `M_EXCLUSIVE: User is not in namespace`.

**Workaround:** via `!admin appservices register` in alice's admins-room
(tuwunel-native, dokumentiert in `docs/appservices.md`). Die Registrierung
landet in tuwunel-DB korrekt mit namespace-regex.

**Wie oft nötig?** Einmal pro tuwunel-DB-lifetime (= einmal nach fresh checkout
oder nach `podman volume rm matrix_tuwunel-data`). `dev-stack.sh` erkennt
automatisch ob's schon registriert ist (via HTTP-code-probe) und skippt.

## Troubleshooting

### `compose up` skippt services nach dem Start

**Ursache:** podman-compose 1.0.6 kennt `--profile` flag nicht — nutzt aber
`COMPOSE_PROFILES` env-var. Wenn gesetzt, **filtert** es **ALLE** services
ohne passendes profile raus (auch default-services!).

**Fix:** dev-stack.sh hat 2-phasen split — default-services (tuwunel, nats,
postgres) separat starten, dann profiled (litellm, calls, ...) mit
COMPOSE_PROFILES. Ist automatisch.

### `Error: creating container storage: ... no such file or directory`

**Ursache:** Podman overlay-storage-corruption (meist durch disk-full
auto-prune der einen image-layer löscht, oder interrupted pulls).

**Fix:**
```bash
podman image prune -af    # removes unused images
podman pull <image>       # re-pull (erstellt fresh layer-struktur)
```

### Go-appservice fails: `olm/olm.h: No such file or directory`

**Ursache:** libolm C-header fehlt oder `-tags goolm` fehlt.

**Fix:** dev-stack.sh spawnt mit `-tags goolm` (pure-Go crypto, kein libolm-C).

### Bridge startet, kein port :8097

**Ursache:** `python -m bridge.app` lädt nur das FastAPI-object, startet
keinen server.

**Fix:** dev-stack.sh nutzt `uvicorn bridge.app:app --port 8097`.

### `M_EXCLUSIVE: User is not in namespace`

**Ursache:** Appservice-registration-bug (siehe §"Warum Admin-Command" oben).

**Fix:** `./scripts/register-appservice.sh` manuell (wird aber normal auto-
triggered vom dev-stack.sh).

### `Error: no such container "tuwunel"` nach `--kill=tuwunel`

**Ursache:** `--kill=<svc>` macht `podman compose stop` (graceful), aber
container bleibt in `Stopped`-state. Das verhindert `volume rm` ("in use").

**Fix:**
```bash
podman rm -f tuwunel
podman volume rm matrix_tuwunel-data
```

Dann fresh start. Für komplettes restart aller services: `--kill` (ohne target).

## DB-Wipe Szenarien

### Nur Tuwunel DB wipen (z.B. test-users loswerden)

```bash
./scripts/dev-stack.sh --kill=tuwunel
podman rm -f tuwunel           # container weg (blockt volume sonst)
podman volume rm matrix_tuwunel-data
./scripts/dev-stack.sh --tuwunel
./scripts/setup-users.sh       # alice+bob neu
./scripts/dev-stack.sh --matrix-chat    # rest, auto-register appservice
```

### Nur Garage wipen (z.B. storage-keys verloren)

```bash
./scripts/dev-stack.sh --kill=garage
podman rm -f garage
podman volume rm matrix_garage-data matrix_garage-meta
./scripts/setup-garage.sh      # regeneriert keys + patcht configs
# tuwunel restart damit neue keys gelesen werden:
./scripts/dev-stack.sh --kill=tuwunel
podman rm -f tuwunel
./scripts/dev-stack.sh --tuwunel
```

### Full wipe (nuclear option)

```bash
./scripts/dev-stack.sh --kill
podman volume rm $(podman volume ls -q | grep matrix_)
./scripts/setup-garage.sh
./scripts/dev-stack.sh --tuwunel --nats --postgres --storage=garage --litellm
./scripts/setup-users.sh
./scripts/dev-stack.sh --matrix-chat
```

## Ports-Überblick

### Aus Image (compose)

| Port | Service |
|---|---|
| 8448 | Tuwunel (Matrix) |
| 4222 | NATS |
| 5433 | Postgres (via mapping von :5432 intern) |
| 3900 | Garage S3 API |
| 3903 | Garage Admin API |
| 4000 | LiteLLM |
| 7880 | LiveKit SFU |
| 8080 | lk-jwt |
| 3478 | coturn TURN |
| 5080 | OpenObserve (opt-in) |

### Lokal (unser Code)

| Port | Service |
|---|---|
| 29318 | go-appservice (Appservice-Callback-URL für tuwunel) |
| 8094 | python-agent (FastAPI via uvicorn) |
| 8097 | python-bridge (NATS↔HTTP-SSE Translator) |
| 8098 | python-ingestion (optional) |
| 3003 | frontend-merger (Next.js dev) |

## Operations Quick-Reference

```bash
./scripts/dev-stack.sh --status          # was läuft?
./scripts/dev-stack.sh --kill            # alles stop
./scripts/dev-stack.sh --kill=tuwunel    # einzeln stop (compose stop)
./scripts/dev-stack.sh --restart=agent   # stop + start einzeln
./scripts/dev-stack.sh --matrix-chat --skip=frontend   # preset minus X
./scripts/dev-stack.sh --calls           # zu laufendem stack dazupacken (additiv)
tail -F logs/devstack/*.log              # alle lokalen prozess-logs
podman logs -f tuwunel                   # container-logs
```

## Known Upstream Bugs

Siehe `specs/execution/exec-matrix-monitor.md` für die volle monitor-liste
(Tuwunel, Element Call, etc.). Relevant für dev-stack:

- `tuwunel#411` S3 large-upload timeout (~200 MiB) — workaround `max_request_size = 100 MB`
- tuwunel v1.6.0 stable appservice-autoload (siehe §"Admin-Command" oben) — wird in v1.6.1 evt. gefixt

## Config-Source-of-Truth

| Was | Wo |
|---|---|
| Tuwunel config | `homeserver/tuwunel.v1.6.toml` |
| Garage config | `homeserver/garage.toml` |
| Appservice-Registration | `homeserver/registration.yaml` + `homeserver/appservices/registration.yaml` (mirror) |
| Go-Appservice env | `go-appservice/.env.development` |
| Python-Agent env | `python-backend/.env.development` (APP_ENV-gesteuert über `shared/app_factory.py`) |
| Frontend env | `frontend_merger/.env.local` |
| Compose services | `docker-compose.yml` |
