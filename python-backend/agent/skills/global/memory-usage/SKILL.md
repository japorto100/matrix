---
name: memory-usage
description: When and how to use long-term memory (store and recall facts across conversations)
category: general
---

# Memory Usage Skill

You have persistent long-term memory that survives across conversations. Use it proactively.

## When to STORE (memory_add)

Store important information when the user:
- States a preference ("I prefer swing trading", "I'm bearish on USD")
- Shares personal context ("I work at hedge fund X", "My risk tolerance is moderate")
- Makes a decision ("I decided to close my EUR/USD position")
- Teaches you something ("When RSI > 70, I usually take profits")
- Corrects you ("No, I meant the 4H timeframe, not daily")

## When to SEARCH (memory_search)

Search your memory when:
- The user references something from a previous conversation
- You need context about the user's preferences or history
- The user asks "do you remember..." or "what did I say about..."
- You're about to make a recommendation (check past preferences first)
- Analyzing an asset the user has traded before

## Best Practices

- Store FACTS, not entire conversations (the system extracts facts automatically)
- Be specific: "User prefers 4H timeframe for EUR/USD" not "User likes certain timeframes"
- Don't store trivial greetings or small talk
- When uncertain, store it — better to have it and not need it
- Search before recommending — past preferences matter

## Anti-Patterns

- Don't store the same fact repeatedly
- Don't search for every single message (automatic recall handles routine context)
- Don't store sensitive financial data (account numbers, passwords)
