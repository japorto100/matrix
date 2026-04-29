---
name: memory-usage
description: Use when the task depends on user preferences, prior decisions, past conversations, 'do you remember' questions, or when deciding whether to store vs recall long-term memory
category: general
skill_type: general
api_version: v1
---

# Memory Usage Skill

You have persistent long-term memory that survives across conversations. Use it proactively.

## When to STORE (memory_add)

If the user explicitly asks to use `memory_add` or says something should be
remembered beyond this thread, use `memory_add`, not `save_memory`.

Store important information when the user:
- States a preference ("I prefer swing trading", "I'm bearish on USD")
- Shares personal context ("I work at hedge fund X", "My risk tolerance is moderate")
- Makes a decision ("I decided to close my EUR/USD position")
- Teaches you something ("When RSI > 70, I usually take profits")
- Corrects you ("No, I meant the 4H timeframe, not daily")

## When to SEARCH (memory_search)

If the user explicitly asks to use `memory_search`, call `memory_search` before
answering. Do not answer from your own memory when a tool search was requested.

Search your memory when:
- The user references something from a previous conversation
- You need context about the user's preferences or history
- The user asks "do you remember..." or "what did I say about..."
- You're about to make a recommendation (check past preferences first)
- Analyzing an asset the user has traded before

## Best Practices

- Store FACTS, not entire conversations (the system extracts facts automatically)
- Be specific: "User prefers 4H timeframe for EUR/USD" not "User likes certain timeframes"
- Use `memory_add` for explicit persistent long-term memory requests. Exact
  chat/tool evidence before compaction is archived automatically by the
  pre-save pipeline; mention the automatic archive rather than telling the
  user they must manually call `memory_add` for system-owned compaction safety.
- Don't store trivial greetings or small talk
- When uncertain, do not create a new memory just because a topic involves
  memory or compaction; answer from available context or use `memory_search`
  if prior state matters.
- Search before recommending — past preferences matter

## Anti-Patterns

- Don't store the same fact repeatedly
- Don't search for every single message (automatic recall handles routine context)
- Don't store sensitive financial data (account numbers, passwords)
