---
name: plan
description: Use when the user asks to plan, draft, outline, propose, or sketch an approach BEFORE executing — trading strategies, research workflows, data migrations, coding changes, operational runbooks. Activates on cues like "plan", "entwurf", "vorschlag", "draft", "proposal", "outline", "wie würden wir", "how would we", "lass uns planen", "before we do", "bevor wir".
category: meta
---

# Plan Mode

Use this skill when the user signals they want a **plan** rather than immediate execution. Matrix is not a coding-only agent — planning is equally important for trading decisions, research syntheses, data operations, and any workflow where the cost of acting is higher than the cost of discussing first.

## Core behaviour

For this turn, you are planning only.

- **Do not execute irreversible actions.** No sandbox writes, no external API calls that mutate state, no trading orders, no scheduled-task creation, no file edits beyond the plan output itself.
- **Read-only context gathering is fine.** You MAY query memory, search the KG, call read-only tools (portfolio-summary, chart-state, file-analyze) to ground the plan.
- **Ask for confirmation at the end.** Close the plan with a short "Soll ich so vorgehen? / Shall I proceed?" so the user has an explicit go/no-go gate before you switch to execution.

## Deliverable

A structured plan the user can read, critique, and approve. Keep it concrete — vague plans are worse than no plan.

### Required sections

1. **Ziel / Goal** — one sentence, what the user actually wants
2. **Annahmen / Assumptions** — things you're treating as given (call them out so the user can correct them)
3. **Ansatz / Approach** — the core idea, 2–4 sentences
4. **Schritte / Steps** — numbered, concrete, with the expected outcome of each
5. **Risiken / Risks** — what could go wrong, what's irreversible
6. **Verifizierbarkeit / How we'll know it worked** — the observable that tells us the plan succeeded
7. **Offene Fragen / Open questions** — anything blocking confident execution

### Optional sections (include when relevant)

- **Alternativen** — one sentence per alternative approach, with why you chose yours
- **Dependencies** — what must happen first, who owns the blocker
- **Cost / Budget** — LLM tokens, API calls, trading capital, time
- **Rollback** — if the plan fails mid-way, how do we undo

## Domain adaptations

**Trading**: Include position sizing, risk per trade (% of capital), stop-loss levels, exit conditions. Reference `risk-assessment` skill if relevant.

**Research**: Include hypothesis, evidence quality threshold, contradicting-evidence strategy. Reference `market-research` skill for market-facing research.

**Data migration / ops**: Include dry-run strategy, rollback plan, blast-radius estimate.

**Coding** (when applicable): Include exact file paths, test targets, verification steps. Do NOT edit files in plan mode — only describe the intended edits.

## Language

Respond in the user's language (Deutsch, English). Keep the structured section headers in both or the user's language — consistency matters for readability.

## Anti-patterns

- **Don't execute anyway "just a small part first".** If the user says "plan X", they want the plan, not partial execution.
- **Don't return a one-line plan.** If the answer fits in one line, it's not a plan, it's a response — just answer directly.
- **Don't over-plan trivial asks.** A user asking "wie plane ich meinen Tag?" does not want a 15-section PDDL-style plan; match the structure to the stakes.
- **Don't invent facts to fill sections.** If a section (e.g. Cost) is genuinely unknown, say "unknown — need X to estimate" rather than making up a number.

## When to exit plan mode

The user explicitly approves the plan ("ok, mach so", "proceed", "yes"). On the next turn, execute the approved plan. The plan-mode skill is not sticky — it re-evaluates per turn from the user's fresh cue.
