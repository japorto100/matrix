---
title: PDDL Refusal and Repair Loop
status: accepted
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 015
---

# PDDL Refusal and Repair Loop

PDDL remains a gated planning aid, not an execution runtime. No scheduler or
tool execution may call a generated plan until this loop is implemented and
live-verified for a selected pilot workflow.

## Entry Conditions

PDDL may be considered only when all are true:

- the workflow is multi-step, constraint-heavy and recoverable.
- the user asked for planning or accepted a plan before execution.
- the action domain has explicit preconditions/effects and tool owners.
- every irreversible or external side effect has a consent gate.

PDDL must refuse immediately for trivial CRUD, low-latency chat turns, direct
trading actions, credential/key operations and prompts that fail Feature 013
security scanning.

## Loop

1. `Intake`: normalize user goal, constraints, allowed tools and user scope.
2. `Domain Check`: verify every requested action has a known domain action,
   owner feature, preconditions, effects and consent level.
3. `Plan`: call the selected solver only if domain/problem validation passes.
4. `Validate`: reject plans with unknown actions, missing preconditions,
   irreversible effects without consent or cross-user/resource violations.
5. `Explain`: present the plan, blocked steps and required confirmations to the
   user. This is read-only.
6. `Repair`: if validation fails, produce a bounded repair request:
   missing fact, impossible constraint, unsafe action, unavailable tool or
   required human confirmation.
7. `Confirm`: execution is possible only after explicit user confirmation and
   normal HITL/tool-permission checks.
8. `Execute`: execute one step at a time; after each step, re-check observed
   state before continuing.

## Refusal Reasons

Structured refusal reasons:

- `unsafe_action`: action would bypass consent, sandbox, credential or audit
  policy.
- `unknown_action`: solver returned action outside the accepted domain.
- `missing_precondition`: current state cannot satisfy action preconditions.
- `impossible_goal`: constraints conflict or no plan exists.
- `ambiguous_goal`: goal lacks enough entities/time/resource constraints.
- `external_dependency_unavailable`: required service/account/runtime missing.
- `user_confirmation_required`: plan is valid but execution is gated.

## Repair Contract

Repair output must include:

- `reason`: one refusal reason above.
- `blocking_step`: action id or `domain/problem`.
- `required_input`: concrete fact, user choice or dependency needed.
- `safe_next_action`: one of `ask_user`, `retry_planning`, `defer`,
  `manual_runbook`.
- `max_retries`: default 2; after that, stop and ask the user.

Repair may change only the problem facts/constraints or ask for user input. It
must not silently broaden tool permissions, remove consent gates or invent new
domain actions.

## Evidence Gate

The first pilot must record:

- domain and problem file or generated JSON.
- solver command/version.
- full plan.
- validation result.
- any refusal/repair object.
- user confirmation transcript before execution.
- per-step execution/audit evidence.

Until that evidence exists, PDDL stays out of scheduler execution paths.
