# exec-20-mcp-manager — MCP Security, Governance & Apps

> Status: Evaluation
> Erstellt: 2026-04-13
> Referenz: `_ref/mcp-manager/` (Git Submodul, Brightwing MCP Manager)
> Abhaengigkeiten: exec-09 (MCP Server + Generative UI), exec-12 (Security), exec-15 (Control UI)

---

## 0. Kontext

MCP ist das zentrale Protokoll fuer unsere Agent-Tool-Integration.
Aktueller Stand in Matrix:
- 4 MCP-Server in `.mcp.json` (agent-openapi, bridge-openapi, ingestion-openapi, matrix-traces)
- Agent IST selbst ein MCP-Server (`agent/mcp_server.py`, `agent/mcp_traces.py`)
- Keine Auth auf MCP-Ebene — alles lokal
- MCP Apps als langfristiges Ziel geplant (06-protocols-roadmap.md, AGENT_TOOLS.md Sek. 3.3)

**Wichtig:** Brightwing MCP Manager ist fuer **Coding-Agents / CLI-Agenten** gedacht
(Claude Desktop, Cursor, VS Code, Codex etc.). Unser Use Case ist ein **Enterprise Agent System**
mit eigenem Backend. Die Konzepte sind uebertragbar, aber nicht 1:1 anwendbar.

---

## 1. Brightwing MCP Manager — Referenz-Analyse

### Was es ist

Tauri Desktop-App (Rust + React) als zentrale MCP-Verwaltung.

| Feature | Implementierung | Relevanz fuer uns |
|---------|----------------|-------------------|
| Auth Proxy | IOTA Stronghold Vault + OS Keychain, Credentials zur Laufzeit injiziert | **Hoch** — Pattern uebertragbar |
| Tool Filtering | Token-Cost pro Tool, per-App Filter-Sets | **Hoch** — direkt relevant fuer Context-Budget |
| Config Discovery | 20+ AI-Tool Config-Pfade (Claude, Cursor, Zed, Amp...) | **Niedrig** — irrelevant, wir haben eigene Config |
| One-Click Install | MCP Scoreboard Integration, Quality Grades | **Niedrig** — wir bauen eigene Server |
| CLI (`bw`) | MCP-Tools direkt aus Terminal aufrufen | **Mittel** — Debug-Nutzung denkbar |
| Registry Governance | Corporate MCP Server Control | **Hoch** — Enterprise-relevant |

### Was NICHT uebertragbar ist

- Desktop-App Architektur (Tauri) — wir brauchen kein Desktop-Tool, sondern Backend-Middleware
- Multi-Tool Config Sync — wir haben ein einziges System, keine 20 AI-Tools zu synchronisieren
- MCP Scoreboard Integration — wir nutzen eigene MCP-Server, keine oeffentlichen

---

## 2. MCP Security Landscape (Stand 13.04.2026)

### Spezifikation

- **MCP 2.4** (2026) mandatiert OAuth 2.1, RFC 8707 Resource Indicators, Tool Sandboxing
- **SEP-2085** — Tool Validation Framework mit SBOM Support
- **CVE-Cluster 2025-2026**: CVE-2025-6514 (Command Injection, CVSS 9.6), CVE-2026-32211 (Zero Auth auf SSE)
- **Audit-Ergebnis:** 41% der 518 untersuchten Produktions-MCP-Server haben KEINE Authentifizierung

### Relevante Open-Source Projekte

#### MCP Proxies / Gateways

| Projekt | Sprache | Features | GitHub |
|---------|---------|----------|--------|
| **MCProxy** (igrigorik) | Rust | Tool Aggregation, Search/Filtering, Middleware-System, Streamable HTTP | `igrigorik/MCProxy` |
| **mcpproxy-go** | Go | Federating Gateway, Security Quarantine, Tool Discovery | `smart-mcp-proxy/mcpproxy-go` |
| **mcp-filter** | TS | Upstream Tool Filtering, **72% Token-Reduktion** | `pro-vi/mcp-filter` |
| **mcproxy** | TS | Tool Filtering fuer Claude Code via `.mcproxy.json` | `team-attention/mcproxy` |

#### Security & Governance

| Projekt | Sprache | Features | GitHub |
|---------|---------|----------|--------|
| **Agent Governance Toolkit** (Microsoft) | Python | Runtime Security, alle 10 OWASP Agentic AI Risks, MCP Security Gateway, sub-ms Policy Enforcement | `microsoft/agent-governance-toolkit` |
| **vault-mcp** | TS | Credential Isolation, AES-256-GCM, Audit Trail | `Chill-AI-Space/vault-mcp` |

#### FastAPI + MCP Auth

| Projekt | Sprache | Features | GitHub |
|---------|---------|----------|--------|
| **fastapi-mcp** | Python | FastAPI Endpoints → MCP Tools mit Auth, OAuth 2.1, MCP 2025-03-26 konform | `tadata-org/fastapi_mcp` |

### Bewertung: Rust vs. Python vs. TS fuer MCP Security

| Aspekt | Rust | Python | TypeScript |
|--------|------|--------|------------|
| Credential Vault | IOTA Stronghold (Brightwing), memory-safe | Kein nativer Vault, `cryptography` lib | Kein nativer Vault |
| MCP Proxy | MCProxy — schnell, Middleware-System | Kein dedizierter Proxy | mcp-filter, mcproxy |
| Auth Integration | Manuell | **fastapi-mcp** — 3 Zeilen OAuth Setup | MCP SDK hat Auth seit Nov 2025 |
| Enterprise Governance | Kein Framework | **Microsoft Agent Governance Toolkit** | Nichts dediziertes |
| Unser Stack | rust_core existiert bereits | Agent-Backend ist FastAPI | agent-chat ist Next.js |

**Empfehlung:**
- **Auth auf MCP-Server:** `fastapi-mcp` fuer unseren Agent MCP Server — passt direkt in FastAPI Stack
- **Proxy/Gateway:** MCProxy (Rust) evaluieren falls wir externe MCP-Server anbinden
- **Governance:** Microsoft Agent Governance Toolkit als Referenz fuer Policy Enforcement
- **Credential Vault:** Bestehendes `agent/security/key_vault.py` erweitern, kein separater Vault noetig

---

## 3. MCP Apps — Langfristiges Ziel

### Was MCP Apps sind (NICHT das gleiche wie MCP Tools/Server)

MCP Apps (SEP-1865, offiziell seit Jan 2026) erlauben MCP-Servern **interaktive UI-Surfaces**
zurueckzugeben statt nur Text/JSON:

- Tool deklariert `ui://...` Ressource in `_meta.ui.resourceUri`
- Host rendert HTML in **sandboxed iframe** (JSON-RPC via postMessage)
- Dashboards, Forms, Visualisierungen, Multi-Step Workflows direkt im Chat
- SDK: `@modelcontextprotocol/ext-apps` ([GitHub](https://github.com/modelcontextprotocol/ext-apps))
- Supported by: ChatGPT, Claude, Goose, VS Code

### Bereits geplant in unseren Docs

- `specs/agent-ui/06-protocols-roadmap.md` Sek. 1.2: MCP Apps als Agent UI Surface
- `main_docs/root/AGENT_TOOLS.md` Sek. 3.3: MCP Apps Extension — evaluate-first
- `specs/execution/exec-15-memory-control-ui.md` Sek. 6.6.3: MCP Apps Liste im Control UI

### Regeln aus Hauptprojekt (beibehalten)

- **MCP Apps als additive Surface**, nicht als Ersatz fuer klassische Tool-Pfade
- **evaluate-first** hinter Feature-Flag; kein globaler Default ohne Evidence
- **text-only Fallback bleibt Pflicht** fuer alle UI-faehigen Tools

### Fuer Enterprise Agent System relevant weil

- Agent kann **interaktive Dashboards** im Chat rendern (Portfolio-Uebersicht, Risk-Matrix, Geomap)
- **Forms** fuer strukturierten User-Input (Trade-Approval, Parameter-Konfiguration)
- **Multi-Step Workflows** visuell begleitbar (Ingestion-Pipeline Status, Backtesting Ergebnisse)
- Standardisiert ueber MCP — funktioniert in agent-chat UND in externen Clients die MCP Apps unterstuetzen

### MCP Apps vs. Unsere bestehenden UI-Patterns

| Pattern | Aktuell | Mit MCP Apps |
|---------|---------|-------------|
| Chart-Rendering | `agent/tools/canvas.py` → Frontend React | `ui://chart` → sandboxed iframe |
| Geomap | `agent/tools/geomap.py` → Frontend | `ui://geomap` → sandboxed iframe |
| Approval Flows | Custom WebSocket Events | `ui://approval-form` → standardisiert |
| Generative UI | Tambo Components | MCP Apps + Tambo (komplementaer, nicht entweder-oder) |

---

## 4. Integrations-Roadmap fuer Matrix

### Phase 1: MCP Auth (Kurzfristig)

- [ ] `fastapi-mcp` evaluieren fuer `agent/mcp_server.py` OAuth 2.1
- [ ] Bearer Token Auth auf `matrix-traces` MCP-Server
- [ ] StreamableHTTP statt SSE fuer nicht-loopback Connections (Spec-Empfehlung)

### Phase 2: Tool Filtering & Token Budget (Mittelfristig)

- [ ] Token-Cost Berechnung pro MCP-Tool Schema (wie Brightwing/mcp-filter)
- [ ] Integration mit bestehendem `context/token_budget.py`
- [ ] Per-Agent Tool-Filtering (nicht jeder Agent braucht alle Tools)

### Phase 3: MCP Apps (Langfristig)

- [ ] `@modelcontextprotocol/ext-apps` SDK evaluieren
- [ ] Erster Prototype: Portfolio-Dashboard als MCP App
- [ ] Integration in agent-chat (iframe Rendering im Chat)
- [ ] Fallback-Pflicht: jede MCP App muss text-only Alternative haben

### Phase 4: Governance (Langfristig, bei Skalierung)

- [ ] Microsoft Agent Governance Toolkit evaluieren
- [ ] Policy Enforcement fuer externe MCP-Server
- [ ] MCP Proxy (MCProxy/Rust oder mcpproxy-go) falls Multi-Server-Setup

---

## 5. Was NICHT uebernommen wird von Brightwing

- Desktop-App / Tauri — wir brauchen Backend-Middleware, kein GUI-Tool
- Multi-AI-Tool Config Discovery — irrelevant, ein System
- MCP Scoreboard / One-Click Install — eigene Server, keine Marketplace
- IOTA Stronghold — wir haben `agent/security/key_vault.py` (AES-256-GCM)

---

## 6. Quellen

### Papers & Specs
- [MCP Authorization Specification (2026)](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [MCP Apps Extension (SEP-1865)](https://github.com/modelcontextprotocol/ext-apps)
- [OWASP Agentic AI Top 10](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)

### GitHub Projekte
- [Brightwing MCP Manager](https://github.com/Brightwing-Systems-LLC/mcp-manager) — `_ref/mcp-manager/`
- [MCProxy (Rust)](https://github.com/igrigorik/MCProxy) — Tool Aggregation, Filtering, Streamable HTTP
- [mcpproxy-go](https://github.com/smart-mcp-proxy/mcpproxy-go) — Federating Gateway
- [mcp-filter](https://github.com/pro-vi/mcp-filter) — 72% Token-Reduktion
- [Microsoft Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) — Runtime Security
- [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp) — FastAPI → MCP mit Auth
- [vault-mcp](https://github.com/rccyx/vault-mcp) — Credential Isolation

### Artikel
- [MCP Security Risks (Security Boulevard, 03/2026)](https://securityboulevard.com/2026/03/model-context-protocol-mcp-security-risks/)
- [Stack Overflow: Auth in MCP (01/2026)](https://stackoverflow.blog/2026/01/21/is-that-allowed-authentication-and-authorization-in-model-context-protocol/)
- [MCP Roadmap 2026 (The New Stack)](https://thenewstack.io/model-context-protocol-roadmap-2026/)
- [MCP Gateway Landscape 2026](https://www.getmaxim.ai/articles/best-mcp-gateways-for-production-systems-in-2026/)
