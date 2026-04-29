---
title: Matrix Widget App Host
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 030
---

# Matrix Widget App Host

## Current State / Ist

Feature 005 now safely renders Matrix widget events as link-cards, not iframes.
The Z_ widget note correctly warns that Element X/FluffyChat support differs
and that widgets are usually room state/events, not arbitrary chat-message HTML.

## Target State / Soll

Feature 030 owns a safe Matrix widget/app host:

- distinguish message markdown, attachments, room-state widgets and generated
  app resources;
- support agent-created widget proposals with user approval;
- render safe links by default and sandboxed iframe/app host only under policy;
- preserve compatibility with Element X, FluffyChat and Matrix web behavior;
- expose deterministic fallback when client cannot render widgets;
- integrate with Feature 024 for MCP/resource policy.

## Boundaries

- Feature 005 owns core chat rendering.
- Feature 008 owns A2UI/generative UI packet rendering.
- Feature 024 owns MCP catalog/resource policy.
- Feature 027 owns report artifacts linked from chat.
- Feature 013 owns sandbox/security/HITL primitives.

Feature 030 owns Matrix widget/app hosting and compatibility policy.

## Closeout Criteria

- Agent-created widget proposals require explicit approval.
- Unsafe widget URLs never execute.
- Compatible clients get room-state/widget behavior; unsupported clients get
  stable markdown/link fallback.
- Sandboxed app host has allowlist, CSP/origin policy and audit events.
- Live verification covers Matrix Web/Element X/FluffyChat where available.
