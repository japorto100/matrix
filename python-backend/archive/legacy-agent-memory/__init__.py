"""Agent Memory — selectable engine integration (exec-11 / exec-memory).

Persistent Memory fuer AI Agents:
- Auto-Retain: Fakten aus Conversations extrahieren
- Auto-Recall: Relevante Memories vor LLM-Call injizieren
- Waehlbare Runtime-Engine: Hindsight oder MemPalace
- Per-User Banks: Isolation pro User

Default bleibt Hindsight; MemPalace kann via `AGENT_MEMORY_ENGINE=mempalace`
aktiviert werden.
"""
