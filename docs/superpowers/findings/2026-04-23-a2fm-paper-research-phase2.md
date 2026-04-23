# A2FM Paper → matrix Phase-2 ML-Router Research

**Date:** 2026-04-23
**Paper:** A²FM: An Adaptive Agent Foundation Model for Tool-Aware Hybrid Reasoning (OPPO AI Agent Team, arXiv 2510.12838v3, Oct 2025)
**Local:** `docs/papers/A2FM-2510.12838v3.pdf` (10 pages + 16 pages appendix/case-studies)
**Related specs:** `exec-a2fm-adaptive-routing.md` (Phase 2+3), `exec-16-llm-provider-gateway.md §2.D`, ADR-001
**Predecessor work:** ADR-001 G1-G4 + P1 (keyword-heuristic router_node landed 2026-04-23)

---

## What A2FM actually is (summary for matrix)

A²FM is a **single unified foundation model** trained from Qwen2.5-32B-Instruct to handle three execution modes via a learned router-as-token mechanism:

| Mode | When | Token output | Cost |
|---|---|---|---|
| **instant** | Trivial factual queries | `<answer>...</answer>` direct | Minimal |
| **reasoning** | Math, logic, multi-step | `<reasoning>CoT</reasoning><answer>...</answer>` | High (CoT tokens) |
| **agentic** | Needs external info / tools | `<plan>` + parallel `<tool_call>` + `<summary>` | Medium + tool costs |

### Route-then-Align architecture (the key trick)

**The router IS the model.** The model emits a `<classification>agentic_agent</classification>` or `reasoning_agent` or `instant_agent` token early in the response, and the subsequent tokens follow mode-specific schemas. No external classifier, no separate router service — it's a single forward pass where routing = token generation.

### Training pipeline

1. **Stage 1 (Route-then-Align SFT):** supervised fine-tuning on ~11k trajectories:
   - 5289 agentic trajectories (teacher: DeepSeek-V3.1)
   - 2829 reasoning trajectories (teacher: DeepSeek-R1)
   - 2890 instant trajectories (teacher: DeepSeek-V3.1)
   - **Difficulty-based sampling:** downsample "always-solved" cases → J-shaped distribution; over-sample ambiguous boundary queries.
   - **Classification-ambiguous label rule:** assign mode = trajectory that achieves highest accuracy on that query (not majority vote).
   - 3 epochs, batch 256, 32k max sequence length, cosine decay LR.

2. **Stage 2 (Adaptive Policy Optimization, APO):** GRPO-based RL (no KL divergence, on-policy only) with multiplicative reward:
   - `r_total = r_accuracy × r_adaptive × r_format`
   - `r_accuracy` = LLM-as-judge binary (1 if judge says correct)
   - `r_adaptive = 1 - p^α` if non-instant mode chosen on easy query (α=2), else 1
     - `p` = empirical success rate of forced-instant rollouts on that query
     - High-p (easy) query + non-instant choice → strong penalty
   - `r_format` = schema compliance binary
   - Rollouts: ρ forced + γ adaptive per query; 12 total; batch 128, 2 epochs.

3. **Tools (agentic mode):** SerpAPI web_search, Jina crawl_page + gpt-5-mini summarizer, nsjail code_execute (5s CPU / 5GB RAM cap).

### Results (32B scale, Qwen2.5-32B-Instruct backbone)

| Benchmark | Score | Type | Ranking vs SOTA |
|---|---|---|---|
| BrowseComp | 13.4% | agentic web-browsing | 3rd (behind DeepDive 14.8%, OAgents 13.7%) |
| GAIA | 57.3 | agentic tool-use | 2nd overall |
| AIME25 | 70.4% | reasoning math-olympiad | competitive with o1 79.2% |
| MATH500 | 95.0% | reasoning math | SOTA among 32B |
| HLE | 16.7% | general | SOTA among 32B |
| **Cost/correct** | **$0.00487** | efficiency | **-45.2% vs pure reasoning, -33.5% vs pure agentic** |

## Where A2FM does NOT apply to matrix

Before lifting anything, the mismatches are load-bearing:

1. **Matrix is provider-agnostic (LiteLLM), not a single foundation model.** We call Claude, GPT, DeepSeek, Qwen, OpenRouter proxies — we don't own the weights. A2FM's "router = token" trick requires training the model; we cannot swap Claude-Sonnet's token vocabulary.
2. **No 32B training infra.** Matrix has no GPU cluster, no DeepSpeed setup, no multi-day training pipelines. The full A2FM training (SFT + APO) is a ~3-week multi-GPU endeavour.
3. **No teacher-model access.** A2FM distills DeepSeek-R1 + DeepSeek-V3.1. Matrix has OpenRouter credentials → those can be rented, but the 11k-trajectory generation cost is non-trivial ($100-$500 depending on model prices).
4. **Matrix is single-agent-with-tools, not mode-switching-agent.** Our LangGraph runner has ONE llm_node per turn that may or may not emit tool_calls. A2FM's 3-mode split (instant/reasoning/agentic) conceptually maps to "no-tool-simple-turn / no-tool-reasoning-turn / tool-calling-turn" — but our architecture doesn't separate them as distinct code paths.
5. **A2FM's agentic mode is "plan once + parallel tool_calls + summary" pattern** — specific to their `<plan>` + `<tool_call>` + `<tool_response>` + `<summary>` template. Matrix uses Anthropic-style tool_use blocks via LiteLLM; the wire format is different.

**Conclusion:** A2FM as-shipped is a **research-benchmark** result, not a drop-in architecture. But several design moves are lift-able.

## What IS lift-able for matrix

Filtered by "implementable with current infra, <2 weeks effort":

### L1 — **Post-hoc mode classification of audit logs** (1-2 days, zero training)

Re-label existing `agent.audit_events` rows by mode using rules derived from the same signals A2FM uses during training:

- `agentic` = any `tool_call` event in the thread
- `reasoning` = no tool_calls + multi-iteration LLM-response thread (iteration > 1)
- `instant` = no tool_calls + single-iteration thread + response length under threshold

Store the derived mode in the `ab_experiments.routing_picked_model` column (already exists post-G4) or extend the schema. Run SQL aggregate: `GROUP BY mode → (count, avg_fitness, avg_cost, avg_duration_ms)`. This gives the first real answer to "what's matrix's actual mode distribution?" — probably not 3-equal, likely 70% instant + 25% agentic + 5% reasoning.

**Value:** ground truth before building anything. Immediately answers exec-a2fm Phase-2 prereq question "welche Queries brauchen Tools, welche nicht?"

### L2 — **Adaptive-reward signal without retraining** (2-3 days)

Take A2FM's `r_adaptive = 1 - p^α` penalty structure and apply it to matrix's existing keyword-heuristic router output as an **evaluation loop**, not a training loop:

- For every routed-cheap turn, retrospectively check: did the user follow up immediately with a rephrase/retry? Did fitness score drop below the primary-model baseline? If yes → `p^α` penalty retroactively.
- Aggregate over N turns per-user per-week → "this user's cheap-route false-positive rate is X%".
- Feed back into per-user threshold tuning (`max_simple_chars`, `max_simple_words`, keyword-set expansion).

**Key insight:** matrix doesn't need to retrain a model — it can use the A2FM reward structure as a **feedback loop to tune the rule-based router's thresholds** per user. The adaptive reward becomes an offline A/B-fitness signal, not an online RL signal.

**Integration points:**
- Scorer `composite_fitness` already exists (`agent/harness/scorer.py`)
- A/B table `ab_experiments.harness_fitness_score` is populated per turn (via §4g eval_id wiring done 2026-04-23)
- Missing: per-user threshold-tuning worker that reads last-N-turns fitness by routing-mode and proposes new thresholds. ~200 LOC scheduler-worker analogous to `HarnessBackfillWorker`.

### L3 — **Small sentence-transformers classifier** (5-7 days)

The matrix spec's original Phase-2 idea (`sentence-transformers` → 3-class softmax) is **weaker** than A2FM's token-router but **compatible** with matrix's architecture because we never control the backend model. Concretely:

- Take the L1 mode-labeled audit logs as training data (~10k samples needed for a small classifier; matrix likely needs to grow the audit corpus first).
- Fine-tune a small encoder (e.g. `all-MiniLM-L6-v2` 22MB, ~200ms inference) for 3-way classification.
- Deploy as part of `router_node.py` — the node already exists (ADR-001 P1); swap the inner rule-match with `classifier.predict(user_message)`.
- Threshold-calibrate using A2FM's J-shaped sampling principle: ensure the training set isn't dominated by "always instant" trivial queries.

**Cost:** CPU inference OK (<100ms latency budget). Training can run on CPU in <1h for small classifier. No GPU needed.

**Risk:** `sentence-transformers` encodes only the user message; A2FM's token router has the full conversation context. For multi-turn threads this may misroute. Mitigation: only use classifier on iteration==0 (same guard as current router_node).

### L4 — **Full A2FM training** (Research-only, deferred)

Not in scope until matrix has:
- GPU cluster (or willingness to rent multi-node) for 3-week training run
- Audit corpus > 100k sessions (need balanced mode distribution for J-shaped sampling)
- Decision to move from provider-agnostic (LiteLLM) to self-hosted-model architecture

This is strictly a Welle-5+ research question, not current engineering.

## Cross-spec implications

- **exec-a2fm-adaptive-routing.md Phase 2:** current description (`sentence-transformers` classifier trained on audit logs) is L3. It's compatible with A2FM paper but weaker by design. Update spec to mention paper-inspired architecture is feasible but deferred.
- **exec-a2fm.md Phase 3 (Self-Improving Router):** maps to L2 adaptive-reward feedback loop — **more implementable than paper-style APO RL.** matrix should run L2 first, treat L3 as optional enhancement.
- **exec-harness §4g.4:** Pareto-dashboards pending frontend. Dashboards should show mode-distribution from L1, per-mode fitness from L2. These become the monitoring layer for any Phase-2 rollout.
- **ADR-003 (DSPy gating):** L2 adaptive-reward loop is also achievable with DSPy+GEPA as the tuning mechanism. The D-7 "GEPA vs LLMSelector vs p1" decision intersects here — any of them could be the optimizer for threshold-tuning. Paper reading before Phase-1 PoC (ADR-003 G(−1).2) should consider L2 as the target flow.
- **ADR-001 Rollout G1-G4 + P1:** the keyword heuristic that landed today is essentially A2FM's Stage-1 "instant mode" classifier but implemented as rules. The keyword-set expansion (G1 DE+EN) is the equivalent of A2FM's data curation step. Matrix is already operating in the paper's conceptual space, just with weaker mechanisms.

## Recommended matrix Phase-2 sequencing (differs from exec-a2fm spec)

The spec says Phase 2 = ML classifier, Phase 3 = self-improving. Paper reading suggests **invert**: Phase 2 should be **feedback loop (L1+L2)** first, Phase 3 optional classifier (L3), Phase 4 research (L4).

| Step | What | Effort | Gate |
|---|---|---|---|
| **P2.a (L1)** | Post-hoc mode labeling of audit logs | 1-2d | First real distribution data |
| **P2.b (L2)** | Adaptive-reward feedback + per-user threshold tuning | 2-3d | Keyword heuristic + threshold loop working |
| **P2.c (L3)** | Optional: small encoder classifier if L2 hits ceiling | 5-7d | Audit corpus >10k |
| **P3 (research)** | Full A2FM training | >>2 weeks | GPU infra + Welle 5+ |

**Gate:** after P2.a, if mode distribution is e.g. 95% instant + 4% agentic + 1% reasoning, the whole adaptive-router question may be moot — just optimize the 95% instant case. Real data answers architectural questions.

## Key open questions (for future sessions)

1. **How many audit events are there in matrix's DB currently?** `SELECT COUNT(*) FROM agent.audit_events WHERE action = 'llm_response'` needed before L1 is feasible. If <1000, audit corpus growth must happen first (i.e. users need to actually use matrix).
2. **Does L2's feedback-loop require Hindsight DB schema extension?** Probably yes — need per-user per-mode fitness history. One additional migration (028?).
3. **Is the 3-mode distinction (instant/reasoning/agentic) the right abstraction for matrix?** Trading queries may need a 4th mode ("financial reasoning with live data") that crosses reasoning+agentic. Would need exec-a2fm § update.
4. **For L4 (full A2FM training) — would OPPO release their checkpoint publicly?** Paper mentions "Open Source: Code, Models" but requires verification. If yes, matrix could skip training and just fine-tune.

## Verdict

**For today's spec:** no code change yet. exec-a2fm.md should be updated to reflect (a) paper has been read + summarized here, (b) Phase-2 sequencing is L1→L2 feedback-loop first (spec previously listed L3 classifier as Phase-2 entry). Leave that to a future spec-edit session.

**For the next implementation session:** **L1 (post-hoc mode labeling)** is the smallest, most valuable first step. ~200 LOC SQL + Python analysis script reading `agent.audit_events` + `agent.ab_experiments`, producing a markdown/CSV report. Zero architectural risk. Tells us whether L2+ is worth it.

**For now:** paper integrated into research corpus, cross-refs updated, specs aligned.
