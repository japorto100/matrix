---
title: Knowledge Graph Live Verify
status: pending
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Live Verify

- Start Matrix Postgres and Python backend.
- Insert or ingest one evidence item.
- Extract one candidate KG claim with evidence refs.
- Promote the claim.
- Query current truth and historical truth.
- Add a correction and verify the older version remains historical only.
- Run KG retrieval with semantic + temporal/access decay.
- Run vector-only, KG-only and fused retrieval on the same query.
- Verify RRF output includes chunk refs and KG claim/entity refs.
- Verify graph context is limited to short explanatory paths.
- Inspect the claim and provenance through `/memory/kg` or successor Control UI.
