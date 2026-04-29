---
title: ADR-0005 Agent Learning Stack Boundaries
status: accepted
owner: filip
created: 2026-04-26
updated: 2026-04-26
affects:
  - 012-memory-context-world-personal-kb
  - 015-scheduler-skills-planning-automation
  - 016-meta-harness-agent-optimization
  - 017-knowledge-graph-bitemporal-claims
sources:
  - https://arxiv.org/abs/2512.12818
  - https://hindsight.vectorize.io/guides/2026/04/23/guide-what-agent-memory-really-means
  - https://mempalace.github.io/mempalace/concepts/memory-stack.html
  - https://github.com/MemPalace/mempalace
  - https://github.com/sentient-agi/EvoSkill
  - https://arxiv.org/abs/2603.02766
  - https://github.com/stanford-iris-lab/meta-harness
---

# ADR-0005 Agent Learning Stack Boundaries

## Decision

Matrix uses a role-separated learning stack:

- **Hindsight** is the default learning memory. It owns durable facts,
  preferences, corrections, summaries, reflections and evolving beliefs.
- **MemPalace** is the evidence and episodic long-context store. It preserves
  verbatim chat/session/tool-output context and supports on-demand deep recall.
- **Knowledge Graph** owns promoted structured world/domain claims with
  temporal validity, provenance and conflict status.
- **Skills** operationalize repeated procedures for Matrix's product domains:
  trading, geopolitical analysis, strategy review, research, risk and source
  quality.
- **Meta-Harness** evaluates and promotes harness, prompt, routing, memory and
  skill behavior using search/holdout scenarios and raw traces.

`memory_fusion` should be treated as memory orchestration, not as a claim that
Hindsight and MemPalace are interchangeable or competing sources.

## Product Scope Boundary

Matrix is not building autonomous coding agents as a product feature in this
phase. Future isolated coding workflows may be a separate feature, but they are
out of scope for Feature 015/016 now.

The current agent focus is trading, geomap/geopolitical analysis, strategy
trading, research and user workflow assistance. Meta-Harness may improve the
agent harness and skills, but it must not silently introduce self-modifying
production behavior or autonomous product-code generation.

## Operational Rules

- Hindsight may be consulted broadly, but it must not replace live market,
  news, price, legal, regulatory or current-world data.
- MemPalace is saved to aggressively at session boundaries and before
  compaction/compression, but recalled selectively when exact evidence,
  historical context, conflict resolution or auditability is needed.
- Skills may be seeded manually, adapted from audited public skills, or evolved
  from traces. Third-party skills are untrusted until reviewed.
- Skill promotion requires evidence from traces, explicit review, or stable
  Meta-Harness gates. One successful task is not enough for a durable skill.
- KG claims require explicit promotion from evidence; neither Hindsight nor
  MemPalace writes active KG truth silently.

## Consequences

- Feature 012 must describe memory orchestration and MemPalace trigger policy.
- Feature 015 must treat EvoSkill/Hermes as references for skill evolution, not
  as a mandate to build coding agents.
- Feature 016 must use Meta-Harness onboarding/domain specs before broad
  implementation and must keep coding-agent product scope out.
- Feature 017 must keep KG claims distinct from memory summaries and verbatim
  evidence.
