---
title: Agentic Report Publishing Quarkdown
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 027
---

# Agentic Report Publishing Quarkdown

## Current State / Ist

Agents can answer in chat and Meta-Harness can write JSON artifacts, but Matrix
does not yet have a reproducible publishing lane for reports, briefs, specs,
slides and audit packets.

## Target State / Soll

Feature 027 evaluates and implements a provider-agnostic report publishing
pipeline using Quarkdown or a fallback Markdown-based renderer:

- agent writes structured source documents;
- renderer builds HTML/PDF/slides/plain text;
- data files, citations and charts are versioned next to the report;
- outputs are reproducible and reviewable in git/CI;
- Matrix chat can link or attach generated artifacts;
- Meta-Harness can score report completeness and source grounding.

## Boundaries

- Feature 019/021 provide retrieval and source artifacts.
- Feature 014 provides traces/eval evidence.
- Feature 030 handles Matrix widget/app presentation.
- Feature 005 handles basic Matrix attachment/link display.

Feature 027 owns report source, build and publication artifacts.

## Closeout Criteria

- A minimal report template exists.
- Renderer install/build path is documented and reproducible.
- Reports carry citations/source refs.
- Agent-generated reports are validated before publication.
- Matrix chat can surface a generated report link or attachment safely.
