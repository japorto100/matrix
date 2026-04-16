# Python Backend — uv Workspace & Cache/Build SOTA (2026)

**Status:** Strategie — in matrix dokumentiert, beim Reverse-Port nach tradeview-fusion anzuwenden
**Stand:** 15.04.2026 — matrix root-pyproject bereinigt, System-Caches auf SSD/HDD sortiert

> **Hinweis:** Diese Spec dokumentiert **Invarianten** (was gelten soll), nicht operative
> Schritte. Sie ergänzt `10-portierung.md` um die Python/Rust/Node-Infrastruktur-Schicht und
> wird beim Reverse-Port nach `tradeview-fusion` spiegelbildlich angewendet.

---

## Ziel

Matrix und tradeview-fusion teilen sich den gleichen Dev-Workflow auf dieser Maschine:
ein einheitlicher Plattenplatz-Plan (SSD/HDD), reproduzierbare Python-Umgebungen
ohne stale Workspace-Configs, saubere Repo-Invarianten (kein hardcoded Build-Pfad,
keine Secrets im Shell-RC), und klar definierte dev-CLI-Verteilung (global vs
per-Projekt).

---

## Ist — matrix (2026-04-15, nach Cleanup)

### Root-pyproject.toml
- `tradeview-fusion-python-backend` (Projektname aus trading-project geerbt)
- `[tool.uv.workspace]` und `[tool.uv.sources]` entfernt — die referenzierten
  Members (`python-agent`, `python-compute`, `python-ingest-workers`) und der
  `rust_core`-Pfad existieren im matrix-Repo nicht
- Dev-Group vollständig (ruff, basedpyright, pytest, maturin, ty, pytest-xdist, stubs)
- Wird aktuell **nicht** aktiv synced — Development läuft unter `python-backend/`

### python-backend/
- Eigenständiges Projekt `matrix-python-backend` (setuptools, namespace-packages
  `agent*, bridge*, memory_engine*, context*, voice*, mock*`)
- `.venv/` auf SSD (shared via uv-Workspace)
- Dev-Group: `ruff, basedpyright, pytest, pytest-asyncio, maturin>=1.7`
- **Workspace-Members** (shared `.venv`, erben root-deps):
  - `agent/` — Main-Service, LangGraph-Orchestration, MCP, LLM-Routing
  - `bridge/` — NATS-Consumer für Go-Appservice
  - `voice/` — LiveKit Voice-Worker
  - `memory_engine/` — KG/Vector/Episodic Store (shared data layer)
  - `mock/` — Test-Mock
  - `ingestion/` — Document-Extraction-Pipeline (kompatible Deps)
- **ISOLIERT** (eigenes `.venv`, eigenes `pyproject.toml` — echte Konflikte):
  - `compute/` — `fastapi==0.116.1` Pin vs Root `>=0.120.3`
  - `kg_pipeline/` — `torch==2.3.1` harter ReLiK-Pin
  - `extraction_layout/` — `pillow<11` Konflikt mit hindsight-api-slim
  - `litellm-gateway/` — transitive `uvicorn<0.22.0` Pin (von uv beim sync erkannt)
  - `rust_core/` — maturin-build (PyO3-Binding)
- `context/`, `retrieval/`, `memory/`, `shared/` bleiben Namespace-Packages
  von `matrix-python-backend` (root) — noch ohne eigenes pyproject

### Build/Cache/System
- `CARGO_TARGET_DIR=~/.cache/cargo-target` global in `.bashrc` (SSD)
- `RUSTC_WRAPPER=sccache`, 10 GB Cache (SSD)
- HDD-Symlinks für cargo registry+git, npm `_cacache`, uv cache, bun cache, pnpm store
- HF_HOME, OLLAMA_MODELS, GOMODCACHE env-vars auf HDD
- JULIA_DEPOT_PATH auf HDD
- Secrets in `~/.bashrc.local` (chmod 600, nicht in Git), sourced vom Ende `.bashrc`

### matrix/package.json
- `rust:*`-Scripts entschärft (kein `CARGO_TARGET_DIR=./...target-local`, kein `cargo.exe`)

---

## Ist — tradeview-fusion / trading-project (Referenz-Struktur, noch nicht migriert)

- `python-backend/pyproject.toml` deklariert uv-Workspace mit Members
  `python-agent, python-compute, python-ingest-workers` — alle existieren real
  unter `python-backend/` (Dir-Namen unterscheiden sich von matrix's `agent/` usw.)
- Kein `.venv/` bisher auf dieser Maschine (never synced)
- `target-local/` (290 MB) + Windows-Reste (`cargo.exe`) noch in `package.json`
- Shell-RC wahrscheinlich mit gleichen Platzhalter-Tokens wie matrix vor Cleanup
- **Struktur-Divergenz zu matrix** ist bewusst: trading-project's Dir-Naming (`python-*`)
  passt zum Workspace-Pattern. matrix hat historisch `agent/` statt `python-agent/` —
  beim Reverse-Port ist die matrix-Struktur auf trading-project zu mappen (nicht umgekehrt)

---

## Soll — Invarianten (für beide Repos)

### Python

| Aspekt | Regel |
|---|---|
| **Venv-Strategie** | Ein `.venv` pro uv-Workspace. Separate venv **nur** bei harten Version-Konflikten → Path-Dependency, nicht Workspace-Member |
| **Virtual workspace root** | Wenn Root-pyproject keine eigenen Deps publiziert: `package = false`, nur organisiert |
| **Dev-Tools** | Standalone-CLIs (ruff, pyright, mypy, pre-commit) **global** via `uv tool install`. Projekt-spezifische Test/Build-Tools (maturin, pytest-plugins) in `[dependency-groups].dev` |
| **Shared Libs** | NIE global. Pro venv reproduzierbar via Lockfile |
| **Konflikt-Isolation** | Subpaket mit hartem Version-Pin (torch, pillow) hat eigenes pyproject + eigenes .venv. Kommunikation via HTTP/stdio, nicht Python-Imports |

### Rust

| Aspekt | Regel |
|---|---|
| **Target-Dir** | Global `CARGO_TARGET_DIR=~/.cache/cargo-target`, cross-project shared |
| **Wrapper** | `RUSTC_WRAPPER=sccache` (content-addressed, parallel-safe) |
| **Installs** | `cargo binstall` für Tools (prebuilt), nicht `cargo install` |
| **Registry** | `~/.cargo/{registry,git}` → HDD-Symlink |

### Node / Bun / pnpm

| Aspekt | Regel |
|---|---|
| **Install-Cache** | Bun/pnpm content-addressed, cross-project Hardlinks — Stores auf HDD |
| **node_modules/** | Pro Projekt auf SSD (Hot-Path Random-IO) |
| **Dev-CLIs** | Global nur wenn standalone (tsc, biome). App-Deps immer pro Projekt |
| **Monorepo** | `workspaces` in root package.json, nicht npm |

### Go

| Aspekt | Regel |
|---|---|
| **`GOMODCACHE`** | HDD (fetch-once) |
| **`GOCACHE`** | SSD default `~/.cache/go-build` (Hot-Path compile cache) |
| **`go install`** | Global in `~/go/bin` (by design) |

---

## Cache/Build/Storage-Matrix — SSD vs HDD

**Entscheidungsregel:** nicht „regenerierbar = HDD". Sondern **Access-Pattern**:

| Pattern | Definition | Beispiele | Ort |
|---|---|---|---|
| **Hot random-IO** | Jeder Build / App-Start / Page-Load / CLI-Shim | sccache, go-build, .venv, node_modules, target/, .next/, mozilla-cache, rustup toolchains, `.local/share/mise` (Shim-Resolution!), IDE-Indexes, Browser-Profiles, flatpak app-state | **SSD** |
| **Fetch-once archive** | Download bei Install, danach kalt | cargo registry+git, npm `_cacache`, uv cache, bun cache, pnpm store, GOMODCACHE, HF_HOME, OLLAMA_MODELS | **HDD** |
| **Große kalte Blobs** | Rarely accessed, long-term | VMs (libvirt), Timeshift-Snapshots, Media, ISOs, Downloads | **HDD** |

**Litmus-Test:** Würde 100-IOPS-HDD auf diesem Pfad beim normalen Dev-Loop auffallen?
→ SSD. Wird der Pfad vielleicht einmal pro Woche gelesen? → HDD ist fein.

**Anti-Patterns (nie tun):**
- Symlink `.venv`, `target/`, `node_modules/`, `.cache/sccache`, `.cache/go-build`,
  `.local/share/mise`, Browser-Profiles zu HDD
- `~/.rustup/toolchains/` auf HDD
- Runtime-Libs (fastapi, pydantic, tokio, react) global installieren

---

## Repo-Invarianten

### package.json
- **Keine** hardcoded `CARGO_TARGET_DIR` in npm-Scripts — erbt aus env
- **Keine** Windows-Pfade (`$HOME/.cargo/bin/cargo.exe`, PowerShell in Linux-Default-Scripts)
- PowerShell-Scripts in separaten `*.ps1`-only Targets (`rust:py:rebuild`) — markiert als Windows-only im Script-Namen oder Comment

### Root-pyproject.toml
- Keine `[tool.uv.workspace]` / `[tool.uv.sources]` die auf nicht-existierende Members zeigen
- Wenn Root kein aktives Projekt: `[tool.setuptools]` und Deps minimal halten, oder auf virtual workspace umsteigen

### Shell-RC
- **Keine Secrets** (Tokens, API-Keys) im Klartext in `.bashrc` / `.zshrc`
- Pattern: `~/.bashrc.local` (chmod 600, nicht in Git), sourced am Ende von `.bashrc` via `[[ -f ~/.bashrc.local ]] && source ~/.bashrc.local`

---

## Agent-Isolation beim Port (nicht in matrix, erst in tradeview-fusion)

In matrix ist `agent/` Workspace-Member (shared `python-backend/.venv`).
Beim Reverse-Port → eigenes venv:

1. `agent/` aus `python-backend/pyproject.toml` `[tool.uv.workspace].members` raus
2. `agent/pyproject.toml` Dep-Liste aktivieren — komplette Dep-Liste als Kommentar
   in `python-backend/agent/pyproject.toml` (Copy-Paste-fertig)
3. `cd agent && uv sync` → `agent/.venv` (~3–4 GB)
4. agent deploy als standalone-Service (Port 8094 + gRPC 9094)

Warum nicht jetzt: matrix = Isolated-Env, agent nicht separat deployed → keine
echte Isolation-Need. In tradeview-fusion = eigener Service → Isolation wertvoll.

---

## Cross-Repo-Porting — Reverse-Port-Checklist (tradeview-fusion)

Beim Reverse-Port von matrix ins Hauptprojekt — zusätzlich zu den Matrix-spezifischen
Schritten in `10-portierung.md`:

1. **Workspace-Sync:** `cd trading-project/python-backend && uv sync` — die Workspace-Members (`python-agent`, `python-compute`, `python-ingest-workers`) existieren bereits, erzeugt erste `.venv/` auf dieser Maschine
2. **package.json entschärfen:** gleiche Edits wie in matrix —
   - `CARGO_TARGET_DIR=./python-backend/rust_core/target-local`-Prefix aus rust:* Scripts raus
   - `$HOME/.cargo/bin/cargo.exe` → `cargo`
   - Nach erstem erfolgreichen Build: `rm -rf python-backend/rust_core/target-local/`
3. **Shell-RC-Hygiene:** prüfen ob Secrets in `.bashrc` oder wenn übernommen von Windows-Setup — raus in `.bashrc.local`
4. **Cache-Layout:** HDD-Symlinks + env-vars aus matrix übernehmen (bereits gesetzt für diese Maschine — tradeview-fusion erbt sie automatisch)
5. **sccache prüfen:** `sccache --show-stats` → nach erstem Rust-Build sollten Hits wachsen
6. **Subpaket-Isolation:** falls tradeview-fusion weitere Subpakete mit harten Version-Pins einführt — eigenen pyproject + separate venv, via HTTP/stdio IPC

---

## Verification

Non-destructive checks, idempotent wiederholbar:

```bash
# Security
rg "ghp_[A-Za-z0-9]{20,}|github_pat_|sk-[A-Za-z0-9]{40,}" ~/.bashrc ~/.zshrc /etc 2>/dev/null
# → 0 Zeilen (kein echter Token)

# Symlinks
for p in ~/.cargo/registry ~/.cargo/git ~/.npm/_cacache ~/.cache/uv ~/.bun/install/cache ~/.julia; do
  test -L "$p" && readlink "$p" | grep -q cold-storage && echo "OK $p" || echo "FAIL $p"
done

# Env
bash -ic 'printenv | grep -E "CARGO_TARGET_DIR|HF_HOME|OLLAMA_MODELS|GOMODCACHE|UV_CACHE_DIR|JULIA_DEPOT_PATH"'

# Repo-Invarianten (matrix)
rg "target-local|cargo\.exe" ~/code/matrix/package.json                                # → 0
rg "tool\.uv\.workspace|ingest-workers.*workspace" ~/code/matrix/pyproject.toml       # → 0
rg "maturin" ~/code/matrix/python-backend/pyproject.toml                              # → ≥1

# Build-Smoke
cd ~/code/matrix && bun test --bail 2>&1 | tail -3
cd ~/code/matrix/python-backend && uv run ruff check . 2>&1 | tail -3
cd ~/code/matrix/python-backend/rust_core && cargo check 2>&1 | tail -3
ls ~/.cache/cargo-target/                                                              # → debug/ oder release/
sccache --show-stats | head -5                                                         # → hits > 0 nach Rebuild
```

---

## Quellen

- `~/code/trading-project/python-backend/pyproject.toml` — SOTA-Referenz für uv-Workspace
- `~/.claude/CLAUDE.md` — System-weite Tool- und Cache-Konventionen
- `~/code/matrix/specs/10-portierung.md` — Matrix→tradeview-fusion Architektur-Port (dieses Spec ergänzt Infrastruktur-Schicht)
- `~/code/matrix/python-backend/kg_pipeline/pyproject.toml` + `extraction_layout/pyproject.toml` — Vorbilder für korrekte Subpaket-Isolation mit Konflikt-Begründung in Kommentaren
