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

- [x] Agent Chat shell/components pass static frontend gates.
- [ ] BFF reaches Go Gateway.
- [ ] Go Gateway reaches Python agent.
- [ ] UI receives response.
- [x] Streaming semantics are documented as final-packet-over-SSE for now.
- [x] A2UI/SSE packet handling tests pass.
- [ ] Streaming final-state behavior is live-verified in browser.
- [ ] Backend-unavailable error state is actionable.

## G2 Tools and Approvals

- [x] Tool-call block builds.
- [x] Large output model/UI split is represented in code.
- [ ] Tool-call block live-renders.
- [ ] Large output model/UI split is live-verified.
- [x] Approval-required action opens approval UI in component tests.
- [ ] Approve path succeeds.
- [ ] Reject path blocks.

## G3 Shared Components

- [x] Code/copy components pass static frontend gates.
- [x] ImagePreview component passes static frontend gates.
- [ ] LocationEmbed works.
- [ ] LocationMap visual render checked.
- [x] Markdown sanitizer blocks XSS in component tests.

## G4 Context / Provenance

- [x] Context degradation flags visible in component tests.
- [ ] Personal memory provenance visible.
- [ ] World context status/provenance visible.
- [ ] Web sources remain intact.
- [x] `contextPressure` visible in component tests.

## G5 Compression / Title

- [x] Compression status endpoint exists/builds.
- [x] Compression indicator component exists/builds.
- [ ] Compression indicator visible behavior live-verified.
- [ ] Session title visible or fallback confirmed.
- [ ] Async title generation dispatch verified or backend-only status recorded.
- [x] Manual feedback marked nice-to-have unless promoted.

## G6 Voice

- [ ] LiveKit room created.
- [ ] STT receives utterance.
- [ ] LLM response path executes.
- [ ] TTS response plays.
- [ ] Latency measured or voice deferred.
