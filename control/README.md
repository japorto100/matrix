# Control Bundle

This folder is a curated import from `tradeview-fusion` for `matrix`.

## Structure

- `control_surface/`
  - Frontend and Next BFF reference for the `/control` surface.
- `files_surface/`
  - Frontend and Next BFF reference for the `/files` surface.
- `storage/`
  - Portable storage core for artifacts, signed URLs, SeaweedFS/S3, and raw snapshot recording.
- `execution_slices/`
  - The execution-owner docs that explain intent, scope, gates, and rollout order.
- `shared/`
  - Small shared reference artifacts such as Prisma schema snapshots.

## Portable Core

These parts are the main adoption targets for `matrix`:

- `files_surface/src/features/files/**`
- `files_surface/src/app/api/files/**`
- `storage/go-backend/internal/storage/**`
- `storage/go-backend/internal/handlers/http/artifact_handler.go`
- `storage/go-backend/internal/requestctx/**`
- `storage/go-backend/internal/contracts/**`
- `storage/go-backend/internal/connectors/base/**`
- `storage/go-backend/internal/connectors/base/source_snapshot_recorder.go`
- `storage/tools/seaweedfs/**`
- `storage/scripts/start-seaweedfs.sh`
- `storage/go-backend/internal/appstate/**`
- `storage/go-backend/internal/handlers/http/app_state_handler.go`
- `storage/go-backend/.env.development`

## Reference-Heavy Parts

These files are useful patterns, but they still depend on broader app/runtime context:

- `control_surface/src/components/GlobalTopBar.tsx`
- `control_surface/src/features/trading/TradingHeader.tsx`
- `storage/go-backend/internal/app/wiring.go`
- connector examples under `storage/go-backend/internal/connectors/{news,acled,crisiswatch,un,ofac,seco,cftc}`

## Notes

- `files_surface` is internally complete enough to study and port with far fewer missing imports.
- `control_surface` now includes the direct shared UI/auth/preferences dependencies it referenced during audit.
- `control_surface` and `files_surface` are now closed on direct `@/` imports inside their copied subtrees.
- the portable Go storage core is locally closed on internal imports across `internal/storage`, `artifact_handler`, `contracts`, `requestctx`, `cache`, and `connectors/base`.
- audit persistence for file/control actions is now included through `internal/appstate` plus `app_state_handler.go`.
- data-adjacent docs for storage, source status, UIL, and persistence now live under `../main_docs/specs/data/` and `../main_docs/references/status.md`.
- `storage/internal/app/wiring.go` is intentionally kept as reference wiring, not as a standalone drop-in. The portable storage core is the smaller set listed above.
- search and reindex are included on the frontend/BFF side, but there is no clearly separable standalone Go search subsystem in the source project to copy as an extra bundle.
- `tools/seaweedfs/data/` was intentionally not copied. Runtime data should be created fresh in `matrix`.
