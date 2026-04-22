# Root-Legacy Next.js Shell — ARCHIVED 2026-04-22

Dies war das **Root-Level `nextjs_tailwind_shadcn_ts` v0.2.0** `package.json`
das seit dem Initial-Commit im Repo lag. Ursprünglich Teil der
tradeview-fusion-Vorgängerversion, die vor dem Merger-Split mit
`frontend_merger/` als einzelner Next.js-App lief.

## Warum archiviert

1. Alle aktive Frontend-Arbeit lebt in `frontend_merger/` — die Root-Shell
   hatte kein `src/`, kein `next.config.*`, kein `tsconfig.json`, kein
   `biome.json`. `bun run dev` wäre sofort mit "src not found" gecrasht.
2. Von 43 Scripts waren nur ~10 (die `rust:*` Chain) noch funktional; die
   zeigten aber alle auf `./python-backend/rust_core/Cargo.toml` und
   können auch aus `frontend_merger/` oder einem neuen Top-Level-Scripts-
   Runner heraus ausgeführt werden.
3. 125 Dependencies + 20 DevDependencies waren dead-weight — beim `bun add`
   in `frontend_merger/` hat bun sie in die falsche `node_modules/`
   gehoisted (siehe session-log 2026-04-22 commit `9d8a7ac`).
4. `prisma` und `cesium` refs → `db:push` broke (keine `prisma/schema.prisma`
   auf repo-Ebene), `cesium:sync` broke (fehlt `scripts/sync-cesium-assets.mjs`).

## Wenn du eine neue Root-App brauchst

Lass die hier liegen und kreier eine neue `frontend_*` Subdirectory für den
neuen Shell. Den root-level `package.json` Weg nicht wieder beschreiten —
Bun/NPM hoisting-issues sind diesen Preis nicht wert.

## Wenn du einzelne Scripts brauchst

Extrahier sie in ein neues `scripts/package.json` oder integrier in die
bereits vorhandenen `scripts/*.sh` Linux-Scripts. Die `rust:*` Chain ist
am einfachsten in einem Makefile oder Cargo-alias weiterzuführen.

## Archive-Datum: 2026-04-22

Committed by: overnight verify-gate sweep (Task #58).
