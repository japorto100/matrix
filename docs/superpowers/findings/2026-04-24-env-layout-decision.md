# Env-layout decision — root + service envs (Docker-compose aligned)

**Date:** 2026-04-24
**Task:** `#46` exec-17 Observability (diskussion im run-up zum openobserve recreate)
**Scope:** Entscheidung wo env-variables leben sollen in einem polyglot monorepo wie matrix. Trigger war der openobserve admin-password panic — wir hatten den wert in python-backend/.env aber nicht in der root .env, wo podman-compose ihn für `${OPENOBSERVE_PASSWORD}` substitution braucht.

## Gewählte strategie — "both, unterschiedliche rollen"

| Datei | Rolle | Wird gelesen von | Beispiel-vars |
|---|---|---|---|
| `/matrix/.env` (root) | **Compose interpolation** — substituiert `${VAR}` im docker-compose.yml zur container-BOOT zeit | podman-compose | `POSTGRES_PASSWORD`, `OPENOBSERVE_USER/PASSWORD`, `LIVEKIT_API_KEY`, `GARAGE_S3_*` |
| `/matrix/python-backend/.env` | **Runtime** — feedt python-agent prozess | python-agent via dotenv | `HINDSIGHT_DB_URL`, `OPENOBSERVE_USER/PASSWORD` (client-auth), `OTEL_ENABLED` |
| `/matrix/go-appservice/.env.development` | **Runtime** — feedt go-appservice prozess | go-appservice via godotenv | `OPENOBSERVE_USER/PASSWORD` (client-auth), OTLP endpoint |
| `/matrix/frontend_merger/.env.development` | **Runtime** — feedt next.js prozess (BFF + build-time `NEXT_PUBLIC_*`) | next.js | `NEXT_PUBLIC_*`, gateway-URL |

## Warum nicht "nur root" oder "nur service"?

### Offizielles docker-compose model (2026 docs)

Verifiziert via [Docker Compose — Set environment variables](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/) und [Best practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/):

- **Root `.env`** = **variable interpolation** für compose-file. Füttert NICHT direkt container env-vars — es ersetzt `${VAR}` bevor compose die container-config an podman übergibt.
- **`env_file:` directive** im service-block = füttert container-env (wie `docker run --env-file`).
- **`environment:` directive** im service-block = inline container-env (kann `${VAR}` aus root `.env` benutzen).

**Unser stack nutzt den dritten pfad**: `docker-compose.yml` hat `environment: ZO_ROOT_USER_PASSWORD: ${OPENOBSERVE_PASSWORD}` — interpoliert aus root `.env`, landet im openobserve-container-environment.

### Warum "nur service" scheiterte

Unser ursprünglicher plan ("dev-stack.sh sourced python-backend/.env vor compose") hätte funktioniert, aber:

- **Fragil**: wer `podman-compose up` manuell aufruft ohne dev-stack.sh kriegt leere substitutions + container panics
- **Gegen docker design**: offizielles compose-model trennt bewusst compose-interpolation (infra-scope) von container-env (runtime-scope)
- **Magisch**: der context-switch "welche service-env für welche container" ist nicht explizit — dev-stack.sh müsste drei services vor compose sourcen, falsche order = falsche werte

### Warum "nur root" scheiterte

- Service-prozesse laufen **außerhalb** von compose (via dev-stack.sh spawns). Sie lesen ihre eigenen .env-files, nicht die root.
- Würde alle secrets in root zentralisieren → scope-bleed, jeder prozess könnte alle secrets lesen
- Kein isolation-by-design

## Die "duplikation" ist kein dedupe-fehler

OPENOBSERVE_PASSWORD taucht in 3 files auf (root + python-backend + go-appservice). **Verschiedene scopes, zufällig gleicher wert**:

1. Root `.env`: **was** öffnet openobserve als admin-account beim boot (ZO_ROOT_USER_PASSWORD)
2. python-backend/.env: **wie** authentisiert sich python-agent als client gegen openobserve (OTLP basic-auth)
3. go-appservice/.env.development: **wie** authentisiert sich go-appservice als client gegen openobserve (OTLP basic-auth)

Dass #1 und #2+#3 dieselbe auth-credential teilen ist eine **auswahl** (alle services auth'en als admin), keine notwendigkeit. Könnte man per-service service-accounts in openobserve anlegen — dann wären die werte unterschiedlich, aber die 3-files-struktur bliebe.

## Konsequenzen für impl

1. Root `.env` bleibt — mit **header-kommentar** der den scope klarstellt (compose interpolation only, keine runtime-envs)
2. Service-envs bleiben für runtime-prozesse
3. Dev-stack.sh braucht **keine** änderung — podman-compose liest root `.env` automatisch
4. Bei neuen container-config-secrets: in root `.env` ergänzen + service-env wenn der client auch zugreifen muss
5. **Echter gefundener bug**: `go-appservice/.env.development` hat `OPENOBSERVE_*` nur auskommentiert → go-traces laufen silent ohne auth-header bei OTEL_ENABLED=true → 401 von openobserve → silent drop. Muss bei #46 ergänzt werden.

## Ausblick

Wenn wir später zu Docker secrets / vault migrieren (production), wird die zweiteilung noch klarer:
- **Secrets** (vault): für production, rotation-friendly
- **Config** (env): dev-only, checked-in `.env.example`

Für dev-workflow bleibt der hier dokumentierte ansatz.

## Cross-refs

- `specs/execution/superpower-impl-log.md §3` — infra/smoke results
- `specs/execution/exec-17-observability-harness-traces.md` — OTel-integration details
- `docs/superpowers/findings/2026-04-24-observability-tier-strategy.md` — frontend-OTel strategie (tier-model)

## Sources

- [Docker Compose — Set environment variables](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)
- [Docker Compose — Best practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)
