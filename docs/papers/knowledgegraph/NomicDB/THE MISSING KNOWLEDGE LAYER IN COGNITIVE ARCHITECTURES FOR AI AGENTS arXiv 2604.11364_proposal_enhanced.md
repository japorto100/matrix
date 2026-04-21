# [PROPOSAL V1.2] — Cognitive Layer Architecture as Policy

**Status:** Proposed Extension
**Extends:** [Issue #100 V1.1](https://github.com/orneryd/NornicDB/issues/100) (Policy-Driven Decay and Scoring)
**Addresses:** Roynard, *The Missing Knowledge Layer in Cognitive Architectures for AI Agents*, [arXiv:2604.11364v1](https://arxiv.org/pdf/2604.11364), §3 (four-layer decomposition), §4 (convergence evidence), §6 (sycophancy gate, null-hypothesis response)
**Date:** 2026-04-20
**Non-backwards-compatible:** Yes. Targets 1.2.0 release alongside V1.1 policy subsystem.

---

## 0. Why V1.2

V1.1 (Issue #100) makes decay and promotion *policy-driven*. That is a necessary but insufficient response to the Roynard category-error critique.

Roynard's argument (§1, §3, §6) is **not** that NornicDB's decay curves are wrong, or that decay is uniform, or that the tier names are hardcoded. It is categorically different:

> "What decays is the agent's attentional relevance to the information (a memory concern, not a knowledge concern). This system conflates 'I have not accessed this recently' with 'this is less valuable,' and those are categorically different propositions." — §1

> "The key design litmus [...] is the distinction between storage-level and query-time properties. Recency is a query-time heuristic [...]. Decay is a storage-level mechanism [...]. A system that treats all four layers with identical storage and retrieval semantics will predictably mishandle at least three of them." — §3

V1.1 answers Roynard's critique by adding a `NO DECAY` flag and a configurable rate. That is correct but not sufficient:

1. **Supersession is not "decay with threshold 0".** A superseded fact is not forgotten — it remains queryable with provenance linking to its successor. There is no V1.1 primitive that expresses "Claim B improves upon Claim A; both persist; the old is marked superseded."
2. **MVCC version-time is not real-world valid time.** `scoreFrom: VERSION` answers "when was this version written into the DB." It does not answer "when was this fact true in the world." Retro-ingestion of historical facts breaks under V1.1 semantics.
3. **Evidence-gated revision is not a score multiplier.** Wisdom promotion is a *state transition* across stability tiers (predictions → core → anchor, §3 para 9–10), gated on *multiple* pieces of structured evidence (corroboration count **+** session span **+** contradiction absence). A single-metric `WHEN reinforcementCount >= 3 APPLY multiplier` is the Cheng et al. sycophancy anti-pattern Roynard warns about (§3 para 10, Ref. 7).

V1.2 addresses these three gaps as **orthogonal primitives** on top of V1.1. It does not replace V1.1. The policy subsystem from Issue #100 remains correct for the Memory-layer decay concern.

---

## 1. The Three Missing Primitives

| Primitive | Paper Layer | Paper Semantics | V1.1 Status | V1.2 Addition |
|---|---|---|---|---|
| **Supersession** | Knowledge | `A superseded_by B`, both preserved, provenance-linked, query-time filter | Missing | First-class edge type, Cypher DDL, retrieval semantics |
| **Bi-Temporal Validity** | Memory | 4 timestamps (system-created, system-expired, real-world-valid, real-world-invalid); see Graphiti [Ref. 31], Zep, MinnsDB [Ref. 21], Semantica [Ref. 12] | MVCC only (2 timestamps) | Optional `validFrom`/`validTo` per node/edge, layered on MVCC |
| **Evidence-Gated Revision** | Wisdom | Stability tiers with state transitions on multi-signal thresholds (corroboration + session span + non-contradiction). Resists sycophancy (§3 para 10, Ref. 7 Cheng et al. *Science* 2026) | Single-metric score multiplier | Stability-tier as node state, DDL transitions with multi-gate predicates, revision log |

These are the minimum set that corresponds to Roynard's three non-Intelligence layers having **distinct persistence semantics**. Intelligence requires no engine primitive (it is ephemeral per-invocation and lives in the agent).

---

## 2. Supersession Layer

### 2.1 Design principles

1. Supersession is an **edge**, not a score or a flag. The graph must preserve both claims.
2. Supersession is **directional and acyclic** per claim chain; cycles are a schema violation.
3. Supersession carries **provenance**: who asserted the new claim, on what evidence, at what system time, valid in what real-world interval (see §3 bi-temporal).
4. Retrieval queries default to "latest non-superseded" but MUST be able to opt in to historical views.
5. Supersession is **not decay**. A supersession-chain length of 50 does not weaken the oldest claim's retrievability under historical query.
6. A claim can be superseded by multiple successors (fork), and a successor can supersede multiple predecessors (merge), producing a DAG. This matches how real scientific supersession works.

### 2.2 Cypher surface

New edge type reserved by the engine:

```cypher
MERGE (old:Claim {id: $oldId})
MERGE (new:Claim {id: $newId})
CREATE (new)-[:SUPERSEDES {
  reason: 'improved_measurement',
  assertedBy: $agentId,
  evidence: ['paper://arxiv/2603.12345', 'experiment://run/4711'],
  assertedAt: datetime()
}]->(old)
```

New DDL for declaring a label as supersession-aware:

```cypher
CREATE KNOWLEDGE SCHEMA research_claim
FOR (n:ResearchClaim)
APPLY {
  SUPERSESSION ENABLED
  SUPERSESSION CHAIN DEPTH UNBOUNDED
  SUPERSESSION PROVENANCE REQUIRED
  DECAY POLICY 'durable_fact'   // inherits V1.1 NO DECAY
}
```

New built-in Cypher functions:

* `supersededBy(n)` — returns the immediate successor(s) as a list of nodes/edges. Empty list if the claim is current.
* `supersedes(n)` — returns the immediate predecessor(s).
* `supersessionChain(n, {direction: 'forward' | 'backward', maxDepth: 10})` — returns the ordered chain with provenance edges.
* `isCurrent(n)` — true iff `supersededBy(n)` is empty. This is the default retrieval filter.
* `asOfAssertion(n, $datetime)` — returns the claim that was the current head of the supersession chain at that system time.

### 2.3 Storage semantics

* Supersession state is stored as graph edges, not as mutable flags on the predecessor node. The predecessor is never modified.
* Deleting a successor does not un-supersede the predecessor; it requires an explicit `UNSUPERSEDE` operation with provenance (who retracted, why).
* Supersession edges are themselves versioned under MVCC and carry their own bi-temporal validity (§3).
* The engine maintains a materialized `current_head` index per supersession chain for O(1) retrieval filtering.

### 2.4 Retrieval semantics

* Default Cypher: `MATCH (n:ResearchClaim) WHERE isCurrent(n) RETURN n` is the intended pattern, and engines should provide a unified-retrieval flag `onlyCurrent: true` (default) that applies this filter transparently.
* Historical opt-in: `MATCH (n:ResearchClaim) RETURN n, supersededBy(n)` returns everything including stale claims.
* Point-in-time: `MATCH (n:ResearchClaim) RETURN asOfAssertion(n, datetime('2025-06-01'))` — combines with §3 bi-temporal for full time-travel queries.
* Unified search metadata adds:

```json
{
  "scores": { "claim-id-12": { "decay": 1.0, "current": true, "chain_depth": 0 } }
}
```

### 2.5 Interaction with V1.1 decay policies

* A label declared `SUPERSESSION ENABLED` should default to `DECAY POLICY 'durable_fact'` (no-decay from V1.1).
* A superseded claim is not auto-archived. Archival of superseded claims is a separate, opt-in retention decision (`ARCHIVE AFTER SUPERSEDED FOR ...`).
* `decayScore()` on a superseded claim returns its base score unchanged; the fact that it is superseded is communicated through `isCurrent()` and retrieval filters, not through a lowered score. This preserves the category separation: decay is not supersession.

### 2.6 Paper-to-primitive mapping

Roynard §3, para 3 (Knowledge layer, LoRA/DoRA example):
> "Paper A's finding has not become false. The correct operation is supersession: recording the relationship between the two claims and marking one as improved upon, while preserving both for provenance and historical queries."

Direct mapping:
- "recording the relationship" → `(new)-[:SUPERSEDES]->(old)`
- "marking one as improved upon" → `isCurrent(old) == false`
- "preserving both for provenance" → predecessor node untouched, edge carries provenance
- "historical queries" → `asOfAssertion()` and chain traversal

---

## 3. Bi-Temporal Validity Layer

### 3.1 Design principles

1. Four timestamps per bi-temporal entity (node or edge), matching Graphiti [Ref. 31] and the standard bi-temporal literature:
   * `system_valid_from` — when this record became visible in the DB (MVCC-derived)
   * `system_valid_to` — when this record stopped being visible (MVCC-derived, null for current)
   * `real_world_valid_from` — when the fact started being true in the world
   * `real_world_valid_to` — when the fact stopped being true in the world (null for still-true)
2. MVCC and real-world time are **independent axes**. Retro-ingestion is a first-class scenario: a fact valid in the real world since 2015 can be ingested in 2026 and must be queryable both at ingestion time and at 2015.
3. Bi-temporal is **opt-in per label/edge-type**. Knowledge claims default to bi-temporal-enabled, Memory events do (for the real-world-event time ≠ observation time case), Wisdom records do not (they are directive-state, not timeline-state).
4. Bi-temporal composes with supersession: a supersession edge has its own bi-temporal validity separate from the claims it links.

### 3.2 Cypher surface

New DDL directive inside a schema declaration:

```cypher
CREATE KNOWLEDGE SCHEMA research_claim
FOR (n:ResearchClaim)
APPLY {
  BITEMPORAL ENABLED
  BITEMPORAL REAL_WORLD_VALIDITY REQUIRED
  SUPERSESSION ENABLED
  DECAY POLICY 'durable_fact'
}
```

New per-operation syntax:

```cypher
CREATE (n:ResearchClaim {
  id: 'lora-95-percent',
  text: 'LoRA achieves 95% of full fine-tuning quality at 0.1% parameters'
})
SET n.realWorldValidFrom = datetime('2021-06-17')
// realWorldValidTo omitted → still valid
// system_valid_from is set by the engine to txn time
```

New Cypher operators:

* `validAt(n, $datetime)` — true iff the node/edge was real-world-valid at the given instant.
* `validBetween(n, $from, $to)` — true iff the node/edge's real-world-validity interval overlaps `[from, to]`.
* `asOf(n, $datetime)` — returns the version of the node visible in the DB as of that **system time** (MVCC point-in-time).
* `asAt(n, $datetime)` — returns the node if it was real-world-valid at that instant (independent of when it was ingested).
* `asOfAsAt(n, $systemTime, $realWorldTime)` — full bi-temporal point-in-time: what did we believe, as of `systemTime`, was true at `realWorldTime`?

### 3.3 Interaction with V1.1 `scoreFrom`

V1.1 defines two values for `scoreFrom`:
* `CREATED` — decay age from entity creation (MVCC origin)
* `VERSION` — decay age from latest visible version (MVCC latest)

V1.2 adds two new values and one modifier:
* `REAL_WORLD_VALID_FROM` — decay age from the real-world validity start. For Memory-layer events where "when did this happen" matters more than "when did we learn about it."
* `REAL_WORLD_OBSERVED` — decay age from `system_valid_from`, i.e., when the agent first learned of the fact. Equivalent to `CREATED` in retro-ingest scenarios but distinct in semantics.
* Modifier: `DECAY AGE CLAMP TO REAL_WORLD_VALID_TO` — if the fact has an explicit `real_world_valid_to` in the past, decay is frozen at that age. Prevents "this fact stopped being true in 2018, but we still slowly decay it in 2026" anti-pattern.

Example:

```cypher
CREATE DECAY POLICY episodic_observation
OPTIONS {
  halfLifeSeconds: 604800,
  scope: 'NODE',
  function: 'exponential',
  scoreFrom: 'REAL_WORLD_VALID_FROM',
  clampDecayAgeTo: 'REAL_WORLD_VALID_TO'
}
```

### 3.4 Temporal query semantics

All four axes of Allen's interval algebra [paper Ref. 12, Semantica] must be expressible:

```cypher
// What did we know about X as of the end of 2025?
MATCH (x:ResearchClaim {id: 'lora-95-percent'})
WHERE validAt(x, datetime('2025-12-31'))
  AND asOf(x, datetime('2025-12-31'))
RETURN x

// When did we first learn this?
MATCH (x:ResearchClaim {id: 'lora-95-percent'})
RETURN x.system_valid_from AS ingestedAt, x.realWorldValidFrom AS trueSince

// Find facts that were true in 2015 but we only learned in 2026
MATCH (x:ResearchClaim)
WHERE x.realWorldValidFrom < datetime('2016-01-01')
  AND x.system_valid_from > datetime('2026-01-01')
RETURN x
```

### 3.5 Paper-to-primitive mapping

Roynard §3, para 5 (Memory layer):
> "Every memory operation produces an immutable event in an append-only event log, with four timestamps following Graphiti's bi-temporal model: system-created, system-expired, real-world-valid, and real-world-invalid."

Direct mapping:
- `system-created` → `system_valid_from`
- `system-expired` → `system_valid_to`
- `real-world-valid` → `real_world_valid_from`
- `real-world-invalid` → `real_world_valid_to`

BEAM temporal-reasoning score (0.12 across all systems, §4) is the empirical evidence that this is the bottleneck. The pilot (§5, table 3) shows +0.150 on temporal-reasoning when the memory-engine has bi-temporal filtering. V1.2 brings that primitive into the engine.

---

## 4. Evidence-Gated Revision Layer (Wisdom)

### 4.1 Design principles

1. Wisdom records are **stateful**: they sit in one of four stability tiers and transition between tiers on structured evidence.
2. Transitions are **gated on multi-signal conjunctions**, not single metrics. At minimum: corroboration count **AND** session span **AND** contradiction absence. Single-metric gates are the Cheng et al. sycophancy failure mode (Ref. 7, §3 para 10).
3. Transitions are **logged** in an append-only revision log with full evidence provenance. Rollback is possible by replaying the log in reverse.
4. Wisdom records are **not subject to decay**. They are subject to *revision* via the gate, not to gradual fading. A never-triggered-again wisdom record stays at its current tier unless actively revised.
5. Wisdom is distinct from Knowledge: Knowledge describes the world, Wisdom describes what-to-do. Same observation can produce entries in both (Roynard §3 para 8, gradient-clipping example).
6. Anchor-tier records resist modification; modifying an anchor requires elevated privilege and logs explicitly.

### 4.2 The four stability tiers

From Roynard §3 para 9, slightly generalized:

| Tier | Paper term | Meaning | Modification policy |
|---|---|---|---|
| T0 | `prediction` | Single-episode-derived directive | Freely churnable; auto-demoted if contradicted once |
| T1 | `candidate` | Observed ≥2 times, not yet cross-session | Auto-demoted on contradiction; promoted by gate |
| T2 | `core` | Corroborated across ≥3 independent sessions | Demoted only on contradiction; promoted by gate |
| T3 | `anchor` | Persisted across ≥10 consolidation cycles without contradiction | Locked; explicit `REVISE ANCHOR` required, logged with elevated auth |

Thresholds are declarative (§4.4), not hardcoded. Paper's 3 and 10 are defaults citing BaseLayer [Ref. 3], not invariants.

### 4.3 Cypher surface

New node-state dimension `stability_tier` reserved by the engine for wisdom-schema labels.

New DDL:

```cypher
CREATE WISDOM SCHEMA coding_preference
FOR (n:BehaviorDirective)
APPLY {
  STABILITY TIERS 'prediction', 'candidate', 'core', 'anchor'
  INITIAL TIER 'prediction'

  PROMOTE FROM 'prediction' TO 'candidate'
    WHEN corroborationCount >= 2
     AND NOT EXISTS (n)-[:CONTRADICTED_BY]->()
     AND sessionSpan >= 1

  PROMOTE FROM 'candidate' TO 'core'
    WHEN corroborationCount >= 3
     AND sessionSpan >= 3
     AND NOT EXISTS (n)-[:CONTRADICTED_BY]->()
     AND DISTINCT sources >= 2

  PROMOTE FROM 'core' TO 'anchor'
    WHEN corroborationCount >= 10
     AND sessionSpan >= 10
     AND NOT EXISTS (n)-[:CONTRADICTED_BY]->()
     AND DISTINCT sources >= 3
     AND consolidationCyclesWithoutContradiction >= 10

  DEMOTE FROM ANY TO 'prediction'
    WHEN EXISTS (n)-[:CONTRADICTED_BY]->()
     AND tier != 'anchor'

  ANCHOR REVISION REQUIRES ROLE 'curator'
  REVISION LOG RETAIN INDEFINITELY
}
```

New Cypher operators:

* `stabilityTier(n)` — returns current tier as a string.
* `canPromote(n, $targetTier)` — evaluates the gate predicate, returns boolean + the list of unmet conditions.
* `promote(n)` — advances to the next tier if the gate passes; logs to revision log. Fails loudly if gate fails.
* `demote(n, $targetTier, $reason)` — explicit demotion with required reason.
* `reviseAnchor(n, $newValue, $reason)` — elevated-auth revision of an anchor-tier record.
* `revisionHistory(n)` — returns the full append-only revision log.

### 4.4 Multi-evidence gate: why conjunction is load-bearing

Roynard §3 para 10 cites Cheng et al. 2026 [Ref. 7]:
> "RLHF-trained models affirm user behavior 50% more than humans, and users rate sycophantic AI 9–15% higher even after disclosure. Gating on approval alone would let sycophantic models promote agreeable-but-incorrect patterns. Gating on structured evidence prevents this."

V1.1's promotion rule `WHEN reinforcementCount >= 3 APPLY 'canonical_tier'` is exactly the single-metric gate Roynard warns about. A sycophantic pattern has high `reinforcementCount` **precisely because** the model agrees with the user repeatedly.

V1.2's gate must be a conjunction over **independent** evidence axes:

| Axis | What it measures | Why it resists sycophancy |
|---|---|---|
| `corroborationCount` | Number of times the directive has been acted on successfully | Single axis: sycophantic pattern can fake this |
| `sessionSpan` | Number of distinct sessions over which the pattern holds | Hard to fake: requires temporal persistence |
| `DISTINCT sources` | Number of distinct provenance roots (user, tool output, test result, external doc) | Hardest to fake: sycophancy is self-reinforcing from one source |
| `NOT EXISTS contradictions` | Absence of recorded contradicting evidence | Catches "agreed initially, later corrected" |
| `consolidationCyclesWithoutContradiction` | Survived N DreamCycle passes | Resists short-term bias |

Gate predicate MUST require at least three of these in conjunction for `core` and above. This is engine-enforceable validation at `CREATE WISDOM SCHEMA` time.

### 4.5 Interaction with V1.1 promotion policies

V1.1 `CREATE PROMOTION POLICY` multipliers remain valid for score-ranking adjustments at retrieval time (the Intelligence-layer query-time heuristic, in Roynard's §3 organizing-principle terms). V1.2 promotion is a *state transition in storage*, not a retrieval-time multiplier. Both coexist:

* V1.1 `PROMOTION POLICY canonical_tier {multiplier: 1.35}` → applied at retrieval scoring.
* V1.2 `PROMOTE FROM core TO anchor WHEN ...` → applied at consolidation / write time, changes the stored `stabilityTier` field.

V1.2 MAY expose the stability tier as an input to V1.1 promotion multipliers:

```cypher
CREATE PROMOTION POLICY wisdom_tier_retrieval_boost
FOR (n:BehaviorDirective)
APPLY {
  WHEN stabilityTier(n) = 'anchor'
    APPLY PROMOTION POLICY 'anchor_retrieval_tier'

  WHEN stabilityTier(n) = 'core'
    APPLY PROMOTION POLICY 'core_retrieval_tier'

  PROMOTION COMPOSE 'max'
}
```

This is the clean separation Roynard argues for: storage state (V1.2) drives query-time ranking (V1.1), but they remain distinct mechanisms.

### 4.6 Paper-to-primitive mapping

Roynard §3 para 9:
> "entries derived from a single episode are predictions (free to churn), entries corroborated across three or more independent sessions stabilize as core patterns, and entries that persist without contradiction across ten or more consolidation cycles earn anchor status and resist modification."

Direct mapping:
- "predictions free to churn" → tier T0, no auto-demotion protection except contradictions
- "core patterns" → tier T2, gate conjunction on corroboration + sessions + sources
- "anchor status resists modification" → tier T3, `ANCHOR REVISION REQUIRES ROLE`

---

## 5. Layer Routing

### 5.1 Layer as a first-class schema dimension

Roynard's pilot (§5, table 3) shows that *routing queries to the correct layer-engine* produces +0.128 improvement, and that routing accuracy is load-bearing (heuristic router reverses the advantage). V1.2 bakes layer assignment into schema so the engine can route automatically.

New schema directive:

```cypher
CREATE LAYER SCHEMA my_app
APPLY {
  LAYER 'knowledge' FOR (:ResearchClaim | :ApiSpec | :UserFact)
  LAYER 'memory'    FOR (:ChatEvent | :ObservationRecord | ()-[:CO_ACCESSED]-())
  LAYER 'wisdom'    FOR (:BehaviorDirective | :ProceduralSkill)
  // Intelligence has no storage primitive; it is the agent runtime
}
```

### 5.2 Default policies per layer

The engine ships with opinionated defaults so operators do not accidentally re-introduce the category error:

| Layer | Default decay | Default supersession | Default bi-temporal | Default stability tiers |
|---|---|---|---|---|
| `knowledge` | `NO DECAY` | enabled, required | enabled, recommended | N/A |
| `memory` | `exponential, halfLife=604800, scoreFrom=REAL_WORLD_VALID_FROM` | disabled | enabled, real-world-valid required | N/A |
| `wisdom` | `NO DECAY` | disabled | disabled | enabled, 4-tier default |
| `intelligence` | N/A (no storage) | N/A | N/A | N/A |

Operators CAN override per-label, but the engine MUST warn (and CAN be configured to reject) any policy combination that violates the category separation — e.g., applying exponential decay to a `knowledge`-layer label without an explicit acknowledgement flag:

```cypher
-- This should fail or warn loudly:
CREATE DECAY POLICY bad
FOR (n:ResearchClaim)   -- declared under knowledge layer
APPLY { DECAY RATE 604800 }
-- ERROR: applying decay to a knowledge-layer label violates category separation.
--        Use SUPERSESSION for knowledge updates, or set
--        OPTIONS { acknowledgeCategoryOverride: true } to proceed.
```

### 5.3 Retrieval routing

Unified search accepts an optional layer filter that engines use to pick the right evaluation strategy:

```json
{
  "query": "what is the current LoRA quality claim?",
  "layer": "knowledge",
  "onlyCurrent": true
}
```

```json
{
  "query": "what did the user say about dark mode yesterday?",
  "layer": "memory",
  "asAt": "2026-04-19T00:00:00Z"
}
```

```json
{
  "query": "what's the user's preferred test framework?",
  "layer": "wisdom",
  "minStabilityTier": "core"
}
```

Multi-layer queries are allowed and produce layered result sections rather than a flat list. This mirrors Roynard's Intelligence-layer orchestration (§3 fig. 1): agent composes results from the three persistent layers at query time.

---

## 6. Summary Mapping Table

| Roynard concern | V1.1 response | V1.2 response |
|---|---|---|
| Fixed decay tiers | Policy-driven decay rates and thresholds | Unchanged (V1.1 is correct at this level) |
| Decay applied to facts | `NO DECAY` flag | `knowledge` layer default + category-override guard + Supersession primitive |
| Hardcoded promotion tiers | `CREATE PROMOTION POLICY` with multipliers | `CREATE WISDOM SCHEMA` with stability-tier state machine + multi-evidence gate |
| MVCC version ≠ real-world time | `scoreFrom: CREATED \| VERSION` | Bi-temporal primitive (four timestamps); `scoreFrom: REAL_WORLD_VALID_FROM`; `asAt()` + `asOf()` + `asOfAsAt()` |
| Supersession of claims | None | First-class `SUPERSEDES` edge, `isCurrent()`, chain traversal, provenance required |
| Sycophancy via single-metric promotion | None; V1.1 `WHEN count >= N APPLY multiplier` is the anti-pattern | Multi-evidence conjunction gate required at schema-creation time; engine rejects single-metric gates for tier ≥ core |
| Layer category errors | None structurally | `CREATE LAYER SCHEMA` + default policies per layer + override-guard |
| BEAM temporal-reasoning = 0.12 | Not addressed | Bi-temporal primitive + `asAt()`; matches Roynard's pilot temporal-reasoning +0.150 delta |
| BEAM contradiction-resolution < 0.05 | Not addressed | Supersession primitive + `isCurrent()` filter; matches Roynard's pilot contradiction +0.106 delta |

---

## 7. Cypher Example: Full Knowledge-Memory-Wisdom Pattern

A worked end-to-end example demonstrating all three primitives composing.

```cypher
-- Bootstrap: declare the layer routing for this app
CREATE LAYER SCHEMA agent_memory
APPLY {
  LAYER 'knowledge' FOR (:Fact)
  LAYER 'memory'    FOR (:UserUtterance)
  LAYER 'wisdom'    FOR (:Preference)
}

-- Knowledge schema: bi-temporal, supersession, no decay
CREATE KNOWLEDGE SCHEMA fact_schema
FOR (n:Fact)
APPLY {
  BITEMPORAL ENABLED
  BITEMPORAL REAL_WORLD_VALIDITY REQUIRED
  SUPERSESSION ENABLED
  SUPERSESSION PROVENANCE REQUIRED
  DECAY POLICY 'durable_fact'  // V1.1 NO DECAY preset
}

-- Memory schema: bi-temporal, decay, no supersession
CREATE KNOWLEDGE SCHEMA utterance_schema
FOR (n:UserUtterance)
APPLY {
  BITEMPORAL ENABLED
  DECAY POLICY 'working_memory'  // V1.1 exponential, 7d half-life
  DECAY AGE CLAMP TO REAL_WORLD_VALID_TO
}

-- Wisdom schema: stability tiers with multi-evidence gate
CREATE WISDOM SCHEMA preference_schema
FOR (n:Preference)
APPLY {
  STABILITY TIERS 'prediction', 'candidate', 'core', 'anchor'
  INITIAL TIER 'prediction'
  PROMOTE FROM 'candidate' TO 'core'
    WHEN corroborationCount >= 3
     AND sessionSpan >= 3
     AND DISTINCT sources >= 2
     AND NOT EXISTS (n)-[:CONTRADICTED_BY]->()
  PROMOTE FROM 'core' TO 'anchor'
    WHEN corroborationCount >= 10
     AND sessionSpan >= 10
     AND DISTINCT sources >= 3
     AND consolidationCyclesWithoutContradiction >= 10
}

-- Ingest: user tells the agent "I prefer dark mode"
-- (1) Memory event
CREATE (u:UserUtterance {id: 'utt-001', text: 'I prefer dark mode'})
SET u.realWorldValidFrom = datetime('2026-04-20T10:00:00Z')

-- (2) Knowledge claim (user's stated preference is a fact about the user)
CREATE (f:Fact {id: 'fact-001', subject: 'user', predicate: 'prefers', object: 'dark_mode'})
SET f.realWorldValidFrom = datetime('2026-04-20T10:00:00Z')

-- (3) Wisdom directive candidate
CREATE (p:Preference {id: 'pref-001', directive: 'use dark theme when rendering UI'})
-- Starts at 'prediction' tier automatically

-- Three months later, the user switches to light mode
CREATE (f2:Fact {id: 'fact-002', subject: 'user', predicate: 'prefers', object: 'light_mode'})
SET f2.realWorldValidFrom = datetime('2026-07-15T08:00:00Z')

CREATE (f2)-[:SUPERSEDES {
  reason: 'user_preference_change',
  assertedBy: 'agent-01',
  evidence: ['utterance://utt-099'],
  assertedAt: datetime()
}]->(f)

-- Query: what's the user's current preference?
MATCH (f:Fact {subject: 'user', predicate: 'prefers'})
WHERE isCurrent(f)
RETURN f.object
-- Returns: 'light_mode'

-- Query: what was their preference in May?
MATCH (f:Fact {subject: 'user', predicate: 'prefers'})
WHERE validAt(f, datetime('2026-05-01'))
RETURN f.object
-- Returns: 'dark_mode'

-- Query: when did we first learn about dark mode preference?
MATCH (f:Fact {id: 'fact-001'})
RETURN f.system_valid_from, f.realWorldValidFrom

-- Query (wisdom): should we auto-apply dark mode in UI rendering?
MATCH (p:Preference {id: 'pref-001'})
WHERE stabilityTier(p) IN ['core', 'anchor']
RETURN p
-- Empty: preference is still 'prediction', directive is not yet load-bearing
```

This single example exercises all three V1.2 primitives: supersession (user's preference superseded), bi-temporal (point-in-time query returns historical truth), and stability-tier (wisdom gate not yet passed → directive not trusted).

---

## 8. Updated Acceptance Criteria

Additions to V1.1's acceptance criteria (Section 12 of Issue #100):

* `SUPERSEDES` is a reserved edge type; direct creation is allowed; deletion requires an `UNSUPERSEDE` operation with provenance
* `isCurrent(n)` returns `true` iff no outbound `SUPERSEDES` edge exists from any claim to `n`
* `asOfAssertion(n, $t)` returns the head of the supersession chain at system-time `$t`
* bi-temporal-enabled entities carry four engine-managed timestamps
* `asAt(n, $rwt)` returns the entity iff it was real-world-valid at `$rwt`
* `asOfAsAt(n, $st, $rwt)` composes MVCC point-in-time with real-world-validity
* `DECAY AGE CLAMP TO REAL_WORLD_VALID_TO` freezes decay age at the closure of real-world validity
* `stabilityTier(n)` returns one of the declared tier names
* multi-evidence gate predicates are required for promotion to tiers ≥ `core`; schema creation rejects single-axis predicates for these tiers
* anchor-tier revision requires the declared role and writes an elevated entry to the revision log
* `CREATE LAYER SCHEMA` declares label-to-layer bindings; engine uses these for default policy selection and retrieval routing
* declaring a decay policy with finite rate on a `knowledge`-layer label without an explicit `acknowledgeCategoryOverride: true` option fails validation
* unified-search queries accept a `layer` filter and `onlyCurrent` / `asAt` / `minStabilityTier` filters
* a single observation can produce entries in multiple layers (knowledge + wisdom + memory) with independent lifecycles; deleting one does not cascade to the others by default
* all pre-existing V1.1 acceptance criteria remain satisfied

---

## 9. Updated Workstreams

Additions to V1.1's workstreams (Section 9 of Issue #100):

**Workstream G: Supersession Subsystem**
- reserve `SUPERSEDES` edge type
- implement `isCurrent` / `supersededBy` / `supersedes` / `supersessionChain` / `asOfAssertion` Cypher functions
- implement materialized `current_head` index per chain
- implement `UNSUPERSEDE` DDL with provenance requirement
- detect and reject supersession cycles at write time

**Workstream H: Bi-Temporal Subsystem**
- engine-managed four-timestamp storage for bi-temporal-enabled entities
- implement `validAt` / `validBetween` / `asAt` / `asOfAsAt` Cypher functions
- extend V1.1 decay resolver to support `REAL_WORLD_VALID_FROM` and `REAL_WORLD_OBSERVED` `scoreFrom` values
- implement `clampDecayAgeTo` modifier
- add real-world-validity indexes for point-in-time query performance

**Workstream I: Wisdom Stability Machine**
- implement `stabilityTier` as a reserved node state
- implement `PROMOTE` / `DEMOTE` DDL with predicate compilation
- implement engine-side validation of multi-evidence-gate requirement for tiers ≥ core
- implement append-only revision log with role-gated anchor revisions
- implement `canPromote` / `promote` / `demote` / `reviseAnchor` / `revisionHistory` Cypher functions

**Workstream J: Layer Routing**
- implement `CREATE LAYER SCHEMA` DDL
- implement default-policy selection per layer
- implement category-override guard (warn/reject on category violations)
- extend unified-search to route queries per layer
- emit `layer` metadata in retrieval responses

**Workstream K: Integration and Migration**
- deterministic migration path from V1.1-only policies to V1.2 layer-declared schemas
- opt-in flag: operators can adopt V1.2 per-label without big-bang migration
- feature-flag gating so V1.1-only deployments continue to work
- documentation of the mapping table in §6 as user-facing migration guide

---

## 10. Open Questions

1. **Graph-global vs per-label layer assignment.** Should a label be in exactly one layer, or is cross-layer membership allowed (a `:Fact` that is both knowledge and memory)? Recommendation: exactly one layer per label; cross-cutting needs two separate labels with a `RELATES_TO` link, mirroring the gradient-clipping example (Roynard §3 para 8).
2. **Supersession DAG forking.** When claim A is superseded by both B and C (branching evidence), does `isCurrent(A)` return false? Recommendation: yes, A is not current; either B or C is, and clients resolve the fork with explicit disambiguation.
3. **Bi-temporal on edges.** Cypher relationships are first-class in NornicDB. Bi-temporal validity on edges (not just nodes) is required for the CO_ACCESSED example (Roynard §6). V1.2 MUST support this symmetrically.
4. **Consolidation cycle definition.** `consolidationCyclesWithoutContradiction` assumes a DreamCycle primitive (Roynard §6 future work). V1.2 leaves this as a counter incremented by an external consolidation job; internal DreamCycle is out of scope.
5. **Revision log storage scope.** Is the revision log per-node or global? Recommendation: per-node, with a global secondary index on timestamp for audit queries.
6. **Role-based auth for anchor revision.** NornicDB does not currently have role-based auth primitives; this is a prerequisite for `ANCHOR REVISION REQUIRES ROLE`. Either scope role-based auth into V1.2 or defer anchor-revision guard to V1.3.

---

## 11. Non-Goals

1. **DreamCycle consolidation engine.** Roynard §6 future work; out of scope for V1.2. V1.2 provides primitives that a consolidation engine would drive; it does not implement the consolidation orchestrator itself.
2. **MemArch-Bench benchmark implementation.** Roynard §6 future work; NornicDB can be evaluated against it once it exists, but V1.2 does not ship the benchmark.
3. **Learned router.** Roynard §5 pilot uses an oracle router and notes a heuristic router reverses the gain. V1.2 provides per-layer query filters but does not ship a learned router; that is agent-side concern, not engine.
4. **Model-weight integration.** Roynard §3 footnote 10 notes wisdom also lives in model weights. V1.2 is purely database-layer.
5. **Replacing V1.1.** V1.2 extends, does not replace. V1.1's decay and promotion policies remain the canonical mechanism for the Memory layer's query-time heuristics.

---

## 12. Backwards Compatibility

* V1.1 DDL continues to work unchanged.
* V1.1 policies on labels that are not layer-declared behave identically to V1.2 absence (no new warnings).
* V1.2 requires opt-in via `CREATE LAYER SCHEMA`; without it, the engine behaves as V1.1.
* The `SUPERSEDES` edge type becomes reserved in V1.2. Existing deployments using `SUPERSEDES` as a user-defined edge type must migrate. Mitigation: detection + rename tool shipped alongside V1.2.
* Bi-temporal fields (`system_valid_from`, `system_valid_to`, `real_world_valid_from`, `real_world_valid_to`) become reserved property names on bi-temporal-enabled labels.
* Release target: 1.2.0. Feature-flag gated during 1.2.0-rc.X preview releases; on by default from 1.2.0 GA.

---

## 13. Response to Roynard's Likely Follow-Up

This proposal was designed against the explicit points in arXiv:2604.11364. A direct-to-author validation request should ask at minimum:

1. Does the four-primitive decomposition (V1.1 decay + V1.2 supersession + bi-temporal + stability-tier) correspond to your §3 four layers, or is there a missing primitive?
2. Is the multi-evidence gate (§4.4 of this proposal) sufficient against the Cheng et al. sycophancy failure mode, or do you recommend additional axes?
3. Does the layer-routing scheme (§5) satisfy the category-separation principle, or do you require a stronger architectural separation (separate engines, not separate schemas on one engine)?
4. Would you run the BEAM pilot (table 3 of the paper) against a V1.2-implementing NornicDB build, and is there a published dataset we can use?

If the answer to (3) is "separate engines required," V1.2 is not sufficient and NornicDB positions as a Memory-layer engine only, deferring Knowledge and Wisdom to companion engines (matching the Roynard companion-implementation pattern, §5 of the paper). That repositioning is a strategic decision for the NornicDB maintainers, not an engineering one.

---

## 14. Deliverables (Additions to V1.1 §14)

* supersession subsystem specification and implementation
* bi-temporal subsystem specification and implementation
* wisdom stability-machine specification and implementation
* layer-routing subsystem specification and implementation
* migration guide from V1.1 to V1.2
* updated user-facing documentation covering the four-layer mental model
* BEAM contradiction-resolution and temporal-reasoning pilot against V1.2
* response letter to the Roynard paper with adoption report
