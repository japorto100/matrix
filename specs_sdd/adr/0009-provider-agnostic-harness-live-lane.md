---
title: Provider-Agnostic Harness Live Lane
status: accepted
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_ids:
  - 011
  - 016
  - 020
---

# Context

GitNexus marked direct changes to the shared LiteLLM client path as CRITICAL
because the singleton client is used by agent turns, proposer calls, user key
validation and graph nodes. The current implementation goal is narrower: remove
`llm-mock` from regular live verification lanes while preserving deterministic
fakes for unit and contract tests.

# Decision

Keep the production LiteLLM client path unchanged for this slice. Add a
provider-agnostic capability and smoke layer beside it:

- regular live lanes must fail closed when they point at `llm-mock`, `mock/*`
  or the deterministic local mock port;
- deterministic fake providers remain allowed only when the caller explicitly
  opts in;
- manifests record non-secret provider data: model id, inferred provider,
  capability metadata, base URL, max output budget, embedding provider/model
  and generic key-presence booleans;
- provider-specific SDK examples remain research inputs, not runtime
  dependencies or prompt contracts.

# Consequences

Feature 011, 016 and 020 can now verify configured-provider readiness without
touching the shared client singleton. A future transport abstraction still
requires separate impact review because it would cross agent runtime, control
API, Meta-Harness and graph-node flows.
