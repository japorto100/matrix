---
title: Matrix Homeserver Connectivity Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 004
---

# Sources

| Source | Role in SDD |
|---|---|
| `specs/01-homeserver.md` | Tuwunel/Zendrite setup, config and homeserver choices. |
| `specs/07-mobile.md` | Mobile app compatibility and Element X expectations. |
| `specs/11-bore-tunnel.md` | Bore/cloudflared/ngrok tunnel options. |
| `specs/12-connectivity.md` | Connectivity decision tree for domain, NAT, IPv6, VPS and federation. |
| `specs/execution/exec-matrix-monitor.md` | Passive upstream monitor and re-check cadence. |
| `specs/execution/exec-blocking.md` | Global blocking items that include Matrix upstream/deployment blockers. |
| `specs/execution/exec2-04-verify-gates.md` | Manual verify gates for mobile, uploads, federation and Tuwunel. |

## Adopted Into Matrix

- Tuwunel is primary for Linux/dev/prod-like path.
- Federation is default-off until deployment decision.
- Mobile/Element X requires HTTPS and `.well-known` correctness.
- Upstream monitor items are not active local tasks unless unblocked.
- URL preview security is owned by Feature 013, but homeserver config must keep
  the decision visible here.
