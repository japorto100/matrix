# Podman Lifehacks — matrix-Stack

**Location**: Repo-root (neben `docker-compose.yml`). Reference-Guide für selektives Service-Management, performance, debugging.

## Selective Service Start

### Einzelne Services / Service-Gruppen

```bash
# Nur spezifische Services (Dependencies werden auto-gestartet):
podman-compose up -d tuwunel postgres
podman-compose up -d nats seaweedfs

# Kombinieren mit --profile:
podman-compose --profile observability up -d openobserve      # nur OpenObserve aus profile
podman-compose --profile calls up -d                          # alle aus calls-profile
```

### Profile-basierte Groups

| Profile | Services | Wann aktiv |
|---|---|---|
| _(default)_ | tuwunel, nats, postgres, seaweedfs | Dev mode, infra-only |
| `prod` | go-appservice, python-bridge, nextjs-chat, + coturn | Full container-deploy, kein native dev |
| `merger` | frontend-merger | Merger containerized |
| `litellm` | litellm | LLM proxy gateway |
| `sandbox` | opensandbox, opensandbox-server | Code-execution sandboxes |
| `mock` | llm-mock | Für BFF-Route-Tests ohne echten LLM |
| `calls` | coturn, livekit-server, lk-jwt-service | Voice/Video calls |
| `cache` | valkey | Redis-fork cache |
| `tunnel` | cloudflared (Quick-Tunnel, free) | External exposure |
| `tunnel-named` | cloudflared-named (mit Token) | Paid named tunnel |
| `observability` | openobserve, otel-collector | Logs/Metrics/Traces |
| `kg-falkor` | falkordb | Redis-based KG (alt. zu Kuzu) |
| `kg-nornic` | nornic | Unified Graph+Vector (alt. zu Kuzu) |
| `storage-garage` | garage | Lightweight Rust-S3 (alt. zu seaweedfs) |

### Dev-Typical Combinations

```bash
# Minimal infra für native-dev:
podman-compose up -d tuwunel nats postgres seaweedfs

# Full dev mit calls:
podman-compose --profile calls up -d

# Full prod emulation:
podman-compose --profile prod --profile merger --profile calls up -d

# Dev ohne LLM (LLM-Mock als stub):
podman-compose --profile mock up -d llm-mock
# Dann in python-backend/.env: LITELLM_BASE_URL=http://localhost:8094
```

## Status & Lifecycle

```bash
# Was läuft?
podman-compose ps
podman ps                          # alternative, zeigt auch manuell gestartete

# Logs:
podman-compose logs -f tuwunel     # tail -f
podman-compose logs --tail=50 postgres

# Restart specific service:
podman-compose restart postgres

# Stop specific (bleibt im State, easy wieder up):
podman-compose stop seaweedfs

# Remove specific:
podman-compose rm -f seaweedfs

# Kompletter Stop:
podman-compose down                # stoppt + entfernt container
podman-compose down -v             # + volumes (DATA LOSS!)
```

## Performance Tips (für i7-2600 + 8GB RAM)

### RAM-Budget pro Service (typical)

| Service | RAM Idle | RAM Active |
|---|---|---|
| tuwunel | ~150 MB | 300-500 MB |
| postgres | ~200 MB | 500 MB |
| seaweedfs | ~100 MB | 300-800 MB |
| openobserve | ~250 MB | 500-800 MB |
| otel-collector | ~80 MB | 150 MB |
| garage | ~80 MB | 150 MB |
| litellm | ~100 MB | 200 MB |
| valkey | ~20 MB | 50-200 MB |
| nats | ~15 MB | 30 MB |

**Konsequenz**: Mit `--profile observability` + `--profile calls` + full prod = >2.5GB nur Container. Native-Dev empfohlen für alles außer Infra.

### Memory-optimized Start

```bash
# Dev: nur infra, alles andere nativ:
podman-compose up -d tuwunel postgres nats seaweedfs
# dann:
./scripts/dev-stack.sh

# Resourcen pro Container limitieren (podman-spezifisch):
podman update --memory=512m tuwunel
podman update --cpu-shares=512 postgres
```

## Advanced: systemd-user-services (modernste Podman-Methode)

Generate systemd-units aus compose — jeder Service individuell start/stop-bar via systemctl:

```bash
cd ~/code/matrix
podman-compose generate-systemd --files --name
# → erstellt ~/.config/systemd/user/container-*.service

systemctl --user daemon-reload
systemctl --user enable container-postgres.service
systemctl --user start container-postgres.service
systemctl --user status container-tuwunel.service
```

**Vorteile**:
- Auto-restart bei crash
- Start bei User-Login
- `journalctl --user -u container-tuwunel` für logs
- Pro-Service enable/disable

## Podman-spezifische Quirks

### rootless (default)

Rootless bedeutet: Container können nicht auf privilegierte Ports (<1024) binden ohne `sysctl net.ipv4.ip_unprivileged_port_start=80`. Alle unsere Services nutzen höhere Ports, kein Problem.

### Podman socket für docker-in-docker (opensandbox)

```bash
# Podman rootless socket path:
echo $XDG_RUNTIME_DIR/podman/podman.sock
# → /run/user/1002/podman/podman.sock

# Starten falls nicht läuft:
systemctl --user enable --now podman.socket

# In root .env: CONTAINER_SOCK=/run/user/1002/podman/podman.sock
```

### host.containers.internal (Container → Host)

Podman 4+ erkennt automatisch Host-IP via `host.containers.internal`. Nutze wenn Container nativ laufende Apps erreichen muss:

```bash
CF_TUNNEL_TARGET=http://host.containers.internal:3003 podman-compose --profile tunnel up -d
```

## Debugging

```bash
# Container-Shell:
podman exec -it tuwunel /bin/sh
podman exec -it postgres psql -U postgres hindsight_dev

# File-Inspection:
podman exec tuwunel cat /etc/tuwunel/tuwunel.toml

# Network-Test zwischen Containern:
podman exec go-appservice ping tuwunel
podman exec go-appservice wget -qO- http://tuwunel:8448/_matrix/client/versions

# Inspect Volume-Content:
podman volume inspect matrix_tuwunel-data
podman volume export matrix_postgres-data | tar tvf - | head

# Restart + follow logs:
podman-compose restart postgres && podman-compose logs -f postgres
```

## Cleanup

```bash
# Unused images (nach testing):
podman image prune -a

# Unused volumes (ACHTUNG — data loss!):
podman volume prune

# Alles (rootless, safer than docker system prune):
podman system prune -a --volumes
```

## KG-Provider Switch (Kuzu default vs FalkorDB vs Nornic)

Kuzu ist **embedded** (kein Container nötig), läuft in-process innerhalb python-backend. Default.

**Switchen auf FalkorDB** (Redis-based):
```bash
podman-compose --profile kg-falkor up -d falkordb
# In python-backend/.env.development:
#   KG_PROVIDER=falkordb
#   KG_FALKORDB_URL=redis://localhost:6380
```

**Switchen auf NornicDB** (Graph+Vector unified):
```bash
podman-compose --profile kg-nornic up -d nornic
# In python-backend/.env.development:
#   KG_PROVIDER=nornic
#   KG_NORNIC_BOLT_URL=bolt://localhost:7687
```

## Storage Switch (SeaweedFS default vs Garage)

SeaweedFS ist in `homeserver/tuwunel.v1.6.toml` als active provider konfiguriert.

**Switchen auf Garage** (lightweight, 1-2GB RAM):
```bash
# 1. Garage starten:
podman-compose --profile storage-garage up -d garage

# 2. Garage S3-Credentials generieren:
podman exec garage /garage key create matrix-key

# 3. tuwunel.v1.6.toml: seaweedfs-block auskommentieren, garage-block aktivieren
#    (siehe Comments im toml-file)

# 4. go-appservice/.env.development: S3-Endpoint + Keys aus Garage übernehmen
#    ARTIFACT_STORAGE_S3_ENDPOINT=http://localhost:3900

# 5. tuwunel + go-appservice restarten
podman-compose restart tuwunel
# go-appservice neu starten via dev-stack.sh
```

Go-Code ist **provider-agnostisch** (`ProviderS3` deckt Garage + SeaweedFS + echtes AWS-S3 ab). Kein Code-Change nötig.

## Tuwunel Version-Switch (v1.5.2 vs v1.6.0-rc)

```bash
# Default: v1.6.0-rc (in root .env)
podman-compose up -d tuwunel

# Fallback auf v1.5.2 wenn v1.6-rc bugs:
TUWUNEL_IMAGE=ghcr.io/matrix-construct/tuwunel:v1.5.2 podman-compose up -d tuwunel

# Bleeding edge:
TUWUNEL_IMAGE=ghcr.io/matrix-construct/tuwunel:latest podman-compose up -d tuwunel
```

## Quick-Start Patterns (cheatsheet)

```bash
# Dev daily start:
cd ~/code/matrix
podman-compose up -d tuwunel postgres nats seaweedfs         # infra
./scripts/dev-stack.sh                                         # apps native

# Stop end-of-day:
./scripts/dev-stack.sh --kill                                  # kills native apps
podman-compose stop                                            # stops containers (state kept)

# Next morning:
podman-compose up -d                                           # restart containers
./scripts/dev-stack.sh                                         # restart apps

# Full wipe + restart (troubleshooting):
podman-compose down -v                                         # STOP + delete volumes ⚠️
podman-compose up -d                                           # fresh start
```
