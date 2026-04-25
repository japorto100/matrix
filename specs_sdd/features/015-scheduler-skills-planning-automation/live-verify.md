---
title: Scheduler, Skills, Formal Planning and Automation Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 015
---

# Live Verify

## Scheduler

- [ ] Create scheduled task.
- [ ] List scheduled task.
- [ ] Pause/resume scheduled task.
- [ ] Edit scheduled task.
- [ ] Run scheduled task now.
- [ ] Wait for cron/tick fire.
- [ ] Confirm Python subscriber runs full agent turn.
- [ ] Confirm Matrix delivery target received output.
- [ ] Confirm `task_executions` row status is completed.
- [ ] Confirm `/control/tasks` renders live DB state.
- [ ] Delete/cancel scheduled task.

## Skills

- [ ] Load global/team/personal skills according to config.
- [ ] Run finder for task-specific query.
- [ ] Run real LLM refiner if feature flag enabled.
- [ ] Run iterative search if feature flag enabled.
- [ ] Confirm skill is injected/used in an agent turn.
- [ ] Confirm audit event for skill use if implemented.

## Planning / PDDL / DSPy

- [ ] Run planning skill smoke prompt.
- [ ] Confirm planning skill does not execute side effects.
- [ ] Confirm execution waits for explicit user confirmation.
- [ ] Run PDDL pilot only if selected.
- [ ] Confirm DSPy gate remains off unless ADR conditions are met.

## Result

pending
