# archive — retired code, kept for history

Modules in this directory are **retired**. They're preserved for git-
archaeology and one-off reference, but nothing under `python-backend/`
should import from them.

| Subdir | Archived at | Replaced by | Reason |
|---|---|---|---|
| `legacy-agent-memory/` | 2026-04-18 (branch `ralph/phase-a-abc-refactor`) | `memory_fusion/` + `memory_fusion.memory_provider` ABC | exec-hermes §3.2 post-migration cleanup — the agent-harness engine selector was the predecessor of `memory_fusion`; all 10 call-sites migrated in commit `aefce78`. |
| `legacy-memory-service/` | 2026-04-18 (branch `ralph/phase-a-abc-refactor`) | — (stub never activated) | FastAPI REST wrapper over `memory_engine/` primitives. Planned "späterer Slice" per `pyproject.toml:161` comment, but **never started**: no service in `docker-compose.yml`, no Python importer of `memory.app`, no external consumer. Revive from archive if the HTTP layer becomes necessary — otherwise `agent/control/*` consumes `memory_engine` directly in-process. |

If you find yourself reading files here to copy behaviour into active code,
stop and either:

1. Pull the needed primitive into the replacing module (e.g. `memory_fusion/`)
   with a clear migration commit + tests, or
2. Promote the archived file back out of `archive/` with a README update.

Both beat quietly restoring the old import paths.
