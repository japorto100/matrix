---
title: Agent Chat Voice Runtime Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
---

# Gates

## G1 Text Chat Runtime

- [ ] Agent Chat shell renders.
- [ ] BFF reaches Go Gateway.
- [ ] Go Gateway reaches Python agent.
- [ ] UI receives response.
- [ ] Streaming semantics are documented and verified.
- [ ] Backend-unavailable error state is actionable.

## G2 Tools and Approvals

- [ ] Tool-call block renders.
- [ ] Large output model/UI split works.
- [ ] Approval-required action opens approval UI.
- [ ] Approve path succeeds.
- [ ] Reject path blocks.

## G3 Shared Components

- [ ] CodeBlock renders with Shiki and copy.
- [ ] ImagePreview works.
- [ ] LocationEmbed works.
- [ ] LocationMap visual render checked.
- [ ] Markdown sanitizer blocks XSS.

## G4 Context / Provenance

- [ ] Context degradation flags visible.
- [ ] Personal memory provenance visible.
- [ ] World context status/provenance visible.
- [ ] Web sources remain intact.
- [ ] `contextPressure` visible.

## G5 Compression / Title

- [ ] Compression status endpoint wired.
- [ ] Compression indicator visible or explicitly open.
- [ ] Session title visible or fallback confirmed.
- [ ] Async title generation dispatch verified or backend-only status recorded.
- [ ] Manual feedback marked nice-to-have unless promoted.

## G6 Voice

- [ ] LiveKit room created.
- [ ] STT receives utterance.
- [ ] LLM response path executes.
- [ ] TTS response plays.
- [ ] Latency measured or voice deferred.
