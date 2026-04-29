---
title: Matrix SDD Constitution
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
adrs: []
---

# Matrix SDD Constitution

## Principles

1. Specs describe intent and current reality before code changes happen.
2. Feature folders are the unit of work; separate execution trees are legacy.
3. Every migrated Legacy source keeps provenance via `migrated_from`.
4. Implementation is not done until verify state is explicit.
5. UI, user-facing, networking, E2EE and agent-runtime work require live verify.
6. Research becomes binding only through `spec.md`, `plan.md`, `tasks.md`, or ADR.
7. Accepted ADRs require affected specs to be updated in the same migration step.

## Binding Machine Baseline

The active development target is the local Linux Mint 22.3 XFCE machine. This is
not a generic cloud baseline. Specs and scripts should assume:

- Linux-first commands and paths unless a legacy Windows path is explicitly
  marked historical or porting-only.
- Hot random-IO artifacts stay on SSD: source trees, `.venv/`, `node_modules/`,
  `target/`, `.next/`, `~/.cache/go-build`, `~/.cache/sccache`, browser
  profiles and toolchain/shim stores.
- Fetch-once archives and large cold blobs may live on `/mnt/cold-storage`:
  cargo registry/git, npm and uv caches, pnpm/bun stores, `GOMODCACHE`,
  `HF_HOME`, `OLLAMA_MODELS`, downloads, VM images and snapshots.
- Secrets live outside committed shell rc files. Use local secret files such as
  `~/.bashrc.local` or service `.env` files that remain untracked.

## Binding Tooling Baseline

The project follows the local toolchain choices documented in `AGENTS.md` and
legacy `specs/08-tooling.md`:

- Rust uses rustup, `sccache`, shared SSD `CARGO_TARGET_DIR`, and `cargo
  nextest` when tests exist.
- Node uses Bun/pnpm through mise/corepack; install caches may be cold, but
  `node_modules/` stays local and hot.
- Python uses `uv`; workspaces share one `.venv` unless dependency conflicts
  require an isolated package environment.
- Go keeps `GOMODCACHE` cold and compile cache hot.
- `rg`/`fd`/`jq`/`yq` are preferred for local investigation, with POSIX tools
  acceptable for scripts or portability.

## Binding Privacy Baseline

Privacy-sensitive Matrix defaults are binding until replaced by an ADR:

- Tuwunel is the preferred homeserver for privacy-sensitive runs.
- Federation stays disabled unless a feature explicitly activates external
  federation.
- URL preview stays disabled by default to avoid SSRF and metadata leaks.
- Local presence may exist for UI feedback, but incoming/outgoing federation
  presence remains disabled.
- Dendrite/Zendrite notes are historical fallback material, not production
  guidance.

## Binding Architecture Boundaries

- Go owns Matrix-facing gateway responsibilities, including appservice intent,
  Matrix event handling and E2EE gateway duties.
- Python owns agent/business logic, skills, memory/context and evaluation-heavy
  workflows.
- `frontend_merger` is the current UI home.
- NATS is the Matrix event handoff bus; Agent Chat uses HTTP/SSE through the
  gateway/BFF path.
- Agent outputs intended for Matrix/mobile compatibility should prefer Matrix
  native event types: `m.text`, `m.image`, `m.file` and deep links instead of
  custom widget rendering.

## Current State vs Target State

Each `features/NNN-*/spec.md` must contain:

- `Current State / Ist`
- `Target State / Soll`
- `Gap`
- `Out of Scope`
- `Acceptance Criteria`

`Current State` can mention partial, broken, obsolete or superseded work. It must
not be rewritten as if the target already exists.

## Execution Rules

- Use `tasks.md` for active work.
- Use `gates.md` for open acceptance/verify gates.
- Use `live-verify.md` for manual runtime proof procedure and evidence notes.
- Use `closeout.md` when a feature is closed, including deviations from plan.
- Use `research.md` for websearch, paper notes, benchmark findings and tool
  comparisons.
- Use `adr/` only for decisions that should constrain future work.
- Unchecked boxes are allowed only for active implementation tasks or true
  verify gates. Convert procedure steps, duplicated gates, historical notes and
  template placeholders to plain bullets.

## Legacy Rules During Migration

- Do not delete or rewrite `specs/` or `docs/superpowers/` during first pass.
- Do not move Superpowers files into `specs/execution/` unless explicitly chosen
  after the mapping pass.
- Prefer linking legacy sources from `MIGRATION_MAP.md` over duplicating whole
  files immediately.
- Mark unknown or ambiguous files as `triage_needed`, not as done.
