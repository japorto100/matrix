---
title: Scheduler, Skills, Formal Planning and Automation Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 015
---

# Closeout

## Built

- Scheduler Phase 1 code paths, scheduler adapter and Go scheduler packages
  exist and pass static tests.
- Scheduler prompt scanner and service-user constants/parity tests pass.
- Skill loader/finder and Plan skill tests pass.
- Skill loader source modes, global/team/personal override order,
  disabled-skill filtering, `api_version` and asset parsing are statically
  covered.
- Skills-Guard backend checks pass.
- PDDL and DSPy are gated research/optimization tracks, not default runtime.

## Not Built

- Live cron tick -> Python subscriber -> agent turn -> Matrix delivery proof.
- Agent Chat UI create-to-DB proof and `/control/tasks` real-DB proof.
- Scheduler Phase 2 routines, alternative delivery, conditions and infra jobs.
- Real-LLM refinement/iterative search/offline refiner verification.
- Hindsight outcome feedback, compliance judge and promotion pipeline.
- PDDL pilot and DSPy MIPROv2 proof gates.

## Deviations From Plan

- Static/build/unit verification is not treated as scheduler closure; live
  delivery evidence is still required.
- PDDL/DSPy remain opt-in/gated and are not silently active automation paths.

## Verify Result

- PASS static: `uv run pytest tests/agent/scheduler tests/agent/skills/test_plan_skill.py tests/agent/test_skill_finder.py tests/agent/security/test_prompt_scanner.py tests/agent/security/test_skills_guard.py -q`.
- PASS static: `uv run pytest tests/agent/skills/test_loader_sources.py tests/agent/test_skill_finder.py tests/agent/skills/test_plan_skill.py -q`.
- PASS static: Go appservice scheduler packages were covered by the earlier
  `go test -tags goolm ./...` run.

## Live Verify Result

Pending: cron/chat/UI scheduler delivery, real-LLM skill refinement and
production-like skill/audit feedback evidence.

## Follow-Ups

- Run scheduler integration gates with Postgres, NATS JetStream, Go appservice
  and Python subscriber.
- Decide first Scheduler Phase-2 slice before implementing routines/delivery
  expansion.
- Promote skill feedback/promotion only after real usage/eval data exists.
- Keep PDDL/DSPy behind ADR gates until explicit pilots pass.
