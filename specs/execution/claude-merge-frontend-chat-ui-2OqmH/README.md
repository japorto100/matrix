# Branch Execs — `claude/merge-frontend-chat-ui-2OqmH`

Ausfuehrungs-Dokumentation der Arbeit auf diesem Branch: was gebaut wurde,
welche Verify-Gates durchlaufen sind, was offen bleibt.

**Zeitraum:** 17.04.2026
**Branch:** `claude/merge-frontend-chat-ui-2OqmH`
**Basis-Commit:** `c260001` (wip: pre-migration snapshot)

## Dateien

| Datei | Inhalt |
|---|---|
| `exec-01-frontend-merger-scaffold.md` | `frontend_merger/` Scaffold — package.json, Configs, Shell (GlobalTopBar/Providers/Landing), Features (Agent/Matrix/Control/Files/Memory), BFF-Routes, Dockerfile |
| `exec-02-envfiles-devstack-compose.md` | `.env.example` fuer 3 Projekte, `scripts/dev-stack.sh` (Linux-Port), `docker-compose.yml` Update mit Tuwunel v1.6 + Profile |
| `exec-03-linter-fixes.md` | golangci-lint 12→0, ruff 51→0 (inkl. pre-existing `memory_fusion/fusion_engine.py` Indentation-Bug gefixt) |
| `exec-04-playwright-verify.md` | Playwright headless smoke 8/8 gruen gegen Prod-Build |
| `exec-05-ui-viewers-polish.md` | **2026-04-18** Extracted aus archiviertem `exec-19 §3.9/§5b.6-§5b.10/§5c.6`: Viewer-Packages (wavesurfer/exifr/xlsx/docx-preview/enhanced-md), Model-Discovery-Polish (URL-state/nuqs, Postgres cache, SWR, filter/sort), Reasoning-Cycle-Button im Composer. |
| `VERIFY-GATES.md` | Verify-Gates-Log pro existierendem exec-01..15 aus `specs/execution/` — was auf diesem Branch verifiziert wurde |

## Gesamt-Status auf Branch-Ende

| Kategorie | Status |
|---|---|
| Frontend `bun install` | ✓ 1100+ Pakete, keine Konflikte |
| Frontend `tsc --noEmit` | ✓ clean |
| Frontend `biome check` | ✓ clean |
| Frontend `bun run build` | ✓ 25 Routen, 16 static pages, standalone output |
| Frontend Playwright smoke | ✓ 8/8 gruen (prod mode) |
| Go `go build ./...` | ✓ clean |
| Go `go vet ./...` | ✓ clean |
| Go `go test -short ./...` | ✓ 9/9 Packages ok |
| Go `golangci-lint run ./...` | ✓ 0 issues (war 12) |
| Python `ruff check .` | ✓ 0 issues (war 51 inkl. 5 pre-existing syntax errors) |
| Container-Stack in VM | ✗ docker.io/ghcr.io 503 in VM, bei dir lokal auf Linux+Podman laeuft's |

## Ordner-Struktur-Konvention

- **`specs/execution/exec-*.md`** — produkt-dauerhafte Slices (exec-01 Homeserver, exec-06 Agent-Chat Integration, exec-15 Control UI, etc.). Branch-unabhaengig.
- **`specs/execution/<branch-name>/`** — pro-Branch-Execs, was DIESER Branch gemacht hat + welche Verify-Gates der ueber-geordneten Execs er beruehrt/vollzogen hat. Ephemer — kann nach Merge archiviert werden.
