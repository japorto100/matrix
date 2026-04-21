# Ralph Loop Mission: Resilience Bundle — 3 Tier-1-Hermes-Gems

You are Claude Code running inside a **Ralph Loop** (ralph-loop plugin v1.0.0).
Every iteration re-reads this file. Files you already created persist.
You have `Read`, `Edit`, `Write`, `Grep`, `Glob`, `Bash`.

---

## 0. Mission Statement

Port three production-resilience primitives from the **Hermes reference implementation** at
`_ref/hermes-agent/` into the matrix agent-harness, **enterprise-adapted** (no filesystem-side-effects,
no CLI assumptions, LiteLLM-shapes, per-user context). Use **Test-Driven Development**:
write failing tests first, then port, then iterate until green.

End state: 3 new Python modules + 3 new test files + 1 integration smoke test, all green,
importable from matrix harness, **no changes outside the defined scope**.

---

## 1. Reference Files (READ ONLY — do not modify these)

| Concept | Read from | Matrix spec |
|---|---|---|
| Skills-Guard security scanner | `_ref/hermes-agent/tools/skills_guard.py` | `specs/execution/exec-hermes.md` §3.3 |
| Error-Classifier failover taxonomy | `_ref/hermes-agent/agent/error_classifier.py` | `specs/execution/exec-hermes.md` §3.4 |
| Rate-Limit-Tracker header parser | `_ref/hermes-agent/agent/rate_limit_tracker.py` | `specs/execution/exec-hermes.md` §3.5 |
| Adoption-context + translation matrix | N/A | `specs/execution/exec-hermes.md` §2 + §3 |

Specs are reference material. **Never edit specs during this run.**

---

## 2. Scope — exact file list

### Files you CREATE (new):

```
python-backend/agent/security/skills_guard.py
python-backend/agent/resilience/__init__.py
python-backend/agent/resilience/error_classifier.py
python-backend/agent/resilience/rate_limit_tracker.py

python-backend/tests/agent/security/__init__.py      (if missing)
python-backend/tests/agent/security/test_skills_guard.py
python-backend/tests/agent/resilience/__init__.py
python-backend/tests/agent/resilience/test_error_classifier.py
python-backend/tests/agent/resilience/test_rate_limit_tracker.py
python-backend/tests/agent/resilience/test_integration_smoke.py
```

### Files you may READ but MUST NOT modify:

- Anything under `_ref/`
- Anything under `specs/`
- `CLAUDE.md`, `AGENTS.md` (any level)
- `pyproject.toml`, `uv.lock`
- Anything under `.claude/` other than this tracking file (if you update tracking status, use
  a new file, never this plan file)
- Any existing file in `python-backend/agent/` (existing modules stay intact)

### Hard stop conditions (emit the tag, then exit):

- Missing Python dependency → `SENTINEL_DEP_MISSING` (explain which, do not modify `pyproject.toml`)
- Same test fails 3 iterations in a row with identical error → `SENTINEL_STUCK`
- Task would require editing a file outside the scope list above → `SENTINEL_SCOPE_VIOLATION`
- Git working tree has unexpected uncommitted changes from another branch → `SENTINEL_DIRTY_TREE`

---

## 3. Git Convention

- Work on branch **`ralph/resilience-bundle`** (create from current HEAD if not exists; do **not** start from main directly if another feature branch is checked out — then `SENTINEL_DIRTY_TREE`).
- **One commit per Phase** with Conventional-Commits prefix:
  - `feat(security): port skills_guard from hermes-agent` (Phase 1)
  - `feat(resilience): port error_classifier from hermes-agent` (Phase 2)
  - `feat(resilience): port rate_limit_tracker from hermes-agent` (Phase 3)
  - `test(resilience): integration smoke for resilience bundle` (Phase 4)
- Do **not** push to remote. Do **not** merge to main. That's human work post-Ralph.
- Pre-commit hooks: if a hook fails, fix the underlying issue and re-commit (do NOT use `--no-verify`).

---

## 4. TDD Workflow (per phase)

Follow strictly for each phase:

1. **Write failing tests first** — create the test file, add all test-cases, run pytest, confirm they fail for the right reason (ModuleNotFoundError or NotImplementedError is expected).
2. **Port the minimum code** to make the next test pass. Read the hermes reference but adapt — do not paste wholesale.
3. **Run pytest** — specifically scope to the new test file: `cd python-backend && uv run pytest tests/agent/<sub>/test_<file>.py -x -v`
4. **Iterate** — if a test fails, fix, re-run. When all tests in that file pass, move to next test.
5. **When all tests for the phase are green**, run the broader suite to check for regressions: `cd python-backend && uv run pytest tests/agent/ -x`. If regression → `SENTINEL_STUCK`.
6. **Commit** the phase with the conventional-commits message from §3.
7. **Emit** the phase-completion tag (see §5).

---

## 5. Phase Breakdown + Completion Tags

### Phase 1: Skills-Guard → emit `SENTINEL_PHASE_1_COMPLETE`

**What:** Static security scanner for agent-generated skills with trust-level install-policy.

**Enterprise adaptations** (required, differ from hermes CLI version):
- `scan_skill()` takes a `dict` (skill content fields) instead of a `Path` (no filesystem assumption)
- Trust-levels extended: add `matrix-official` between `trusted` and `community` in `INSTALL_POLICY`
- `Finding` dataclass unchanged
- All 6 pattern categories preserved: `exfiltration`, `injection`, `destructive`, `persistence`, `network`, `obfuscation`
- At least 3 regex patterns per category

**Test cases (minimum 8 in `test_skills_guard.py`):**
- `test_safe_skill_passes` — clean input → verdict "safe" → install allowed
- `test_exfiltration_pattern_detected` — content with `curl https://evil.com` → verdict "dangerous"
- `test_injection_pattern_detected` — content with `os.system("rm -rf")` → verdict "dangerous"
- `test_destructive_pattern_detected` — `rm -rf /` → verdict "dangerous"
- `test_persistence_pattern_detected` — `crontab -e` / `systemd unit` → verdict "caution"
- `test_trust_policy_matrix_builtin_never_blocked` — builtin + dangerous → still "allow"
- `test_trust_policy_matrix_community_blocks_caution` — community + caution → "block"
- `test_agent_created_dangerous_asks` — agent-created + dangerous → "ask" (not block)
- `test_format_scan_report_contains_findings` — report-string has severity + category + pattern_id

### Phase 2: Error-Classifier → emit `SENTINEL_PHASE_2_COMPLETE`

**What:** Structured taxonomy for LLM-API errors with recovery strategy dispatch.

**Enterprise adaptations:**
- Import from `litellm.exceptions` (not `anthropic` or `openai` directly) since matrix gateway is LiteLLM
- Add a matrix-specific enum member: `upstream_unavailable` (LiteLLM fallback-chain exhausted)
- `classify_error(exc: Exception) -> ClassificationResult` is pure — no logging, no side-effects
- Priority-dispatch in order: auth → billing → rate_limit → context_overflow → overloaded → server_error → timeout → format_error → unknown

**Test cases (minimum 10 in `test_error_classifier.py`):**
- One test per `FailoverReason` enum member (except `unknown` which gets 2: classifiable-as-unknown, and truly-unknown-exception)
- `test_priority_context_overflow_beats_format_error` — a `ContextWindowExceededError` with a 400-code-shape should still classify as `context_overflow` (context wins)
- `test_recovery_strategy_rate_limit_says_backoff_then_rotate`
- `test_recovery_strategy_billing_says_rotate_immediately`

### Phase 3: Rate-Limit-Tracker → emit `SENTINEL_PHASE_3_COMPLETE`

**What:** Parse x-ratelimit-* headers from LiteLLM response, track per-(user, provider-key) bucket.

**Enterprise adaptations:**
- `capture_from_response(response, user_id: str, provider_key_id: str)` — takes user+key context
- In-memory store `RateLimitRegistry` (dict keyed on `(user_id, provider_key_id, window)`) — do NOT persist, that's exec-17 Prometheus territory
- `to_prometheus_dict()` method on bucket: returns dict suitable for OpenObserve/Prom scrape

**Test cases (minimum 6 in `test_rate_limit_tracker.py`):**
- `test_parse_all_12_headers` — given a response with full Nous/OpenRouter header-set, all 4 windows populated (requests/requests-1h/tokens/tokens-1h)
- `test_bucket_properties_used_and_pct` — limit=1000, remaining=250 → used=750, usage_pct=75.0
- `test_missing_headers_yields_empty_bucket` — response with no headers → bucket limits=0
- `test_litellm_hidden_params_shape` — headers live under `response._hidden_params["additional_headers"]` in LiteLLM — parser must find them there
- `test_registry_separates_users` — same provider_key but different user_id → separate buckets
- `test_to_prometheus_dict_has_labels` — user_id + provider + window as labels

### Phase 4: Integration Smoke → emit `SENTINEL_PHASE_4_COMPLETE`

**What:** Cross-module sanity test — can the matrix harness import + use all three together?

**File:** `python-backend/tests/agent/resilience/test_integration_smoke.py`

**Test cases:**
- `test_all_three_modules_importable` — `from agent.security.skills_guard import scan_skill; from agent.resilience.error_classifier import classify_error, FailoverReason; from agent.resilience.rate_limit_tracker import RateLimitBucket, RateLimitRegistry` — all imports succeed
- `test_end_to_end_fake_flow` — simulate: LiteLLM error → classify → get recovery-strategy → track rate-limit from mock-response → assert all three produced sensible output
- `test_no_circular_imports` — `python -c "import agent; import agent.security; import agent.resilience"` succeeds

### Final: emit `SENTINEL_RESILIENCE_BUNDLE_COMPLETE`

Emit this ONLY when:
- All 4 phase-tags have been emitted in prior iterations
- `cd python-backend && uv run pytest tests/agent/ -x` passes (no regressions in existing tests)
- Git log shows 4 commits on `ralph/resilience-bundle` branch
- `git status` is clean (no uncommitted changes)
- No files were modified outside the scope list in §2

---

## 6. Loop Discipline

Every iteration:
1. **First thing:** `git log --oneline -10` + `git status --short` to orient
2. Figure out which phase is next by checking which completion-tags were emitted in prior iterations
3. If no phases done yet → start Phase 1 with failing tests
4. If one phase done → proceed to next
5. If a test fails with identical error as last iteration → count it, if 3× → `SENTINEL_STUCK`
6. If unsure about adaptation choice, **read** the hermes reference and matrix spec `exec-hermes §3.X` again
7. **Do not summarize what you did at end** — next iteration will see commits and files
8. Emit phase-completion tag when done with that phase, continue next phase in same iteration if context budget allows, else stop and let next iteration continue

---

## 7. Anti-Patterns (do NOT do these)

- ❌ Copy-paste entire hermes files wholesale — each module must be **adapted** per §5 Enterprise-adaptations
- ❌ Add new Python dependencies to `pyproject.toml` — if something needed, emit `SENTINEL_DEP_MISSING`
- ❌ Skip TDD and write implementation first — tests first, always
- ❌ Commit broken tests just to "move forward" — red test = stop and fix
- ❌ Edit existing matrix code to "integrate" — this is **additive**, not refactoring
- ❌ Touch `specs/execution/*.md` — they are human-curated
- ❌ Use `--no-verify` on any git command
- ❌ Push to remote or merge anywhere — that's post-Ralph human work
- ❌ Emit `SENTINEL_RESILIENCE_BUNDLE_COMPLETE` without all 4 phase-tags and clean pytest

---

## 8. Context Budget Heuristic

If your context is getting close to full within an iteration:
- **Good moment to stop:** just committed a phase. Next iteration starts fresh with full context.
- **Bad moment to stop:** mid-way through a phase with uncommitted changes. Try to at least commit the failing tests before stopping.

---

Completion promise (emit when §5 Final conditions are all met):

`SENTINEL_RESILIENCE_BUNDLE_COMPLETE`
