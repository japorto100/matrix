## Stand 29.04.2026: meine klare Empfehlung

Für ein **Enterprise Python Agent Harness** würde ich es nicht als „ein Agent mit 80 MCP-Tools im Prompt“ bauen, sondern als **Gateway + Tool-Katalog + Policy + Code-Execution-Schicht**.

Das Ziel ist:

```text
LLM sieht nur:
  - wenige Kernwerkzeuge
  - Tool-Suche
  - kurze Tool-Summaries
  - Ergebniszusammenfassungen

Harness sieht:
  - alle MCP-Server
  - alle Schemas
  - Auth, Policy, Audit, Sandboxing
  - Rohdaten und Zwischenresultate
```

MCP ist laut aktueller Spezifikation ein JSON-RPC-basiertes Protokoll mit Hosts, Clients und Servern; Server liefern Ressourcen, Prompts und Tools, während Clients unter anderem Sampling, Roots und Elicitation anbieten können. Wichtig: MCP ist nicht nur „Function Calling“, sondern eine Integrationsschicht mit Lifecycle, Transport, Auth, Session- und Sicherheitsregeln. ([Model Context Protocol][1])

---

# 1. SOTA-Blueprint für dein Enterprise Python Agent Harness

## Zielarchitektur

```text
┌───────────────────────────────────────────────┐
│                User / App UI                  │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│        Orchestrator LLM / Planner Agent        │
│  sieht: search_tools, execute_plan, read_file  │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│          Python Enterprise Agent Harness       │
│  - Tool catalog                                │
│  - Tool search                                 │
│  - MCP gateway                                 │
│  - Policy engine                              │
│  - Audit logging                               │
│  - PII redaction                               │
│  - Output compaction                           │
│  - Sandbox dispatcher                          │
└─────────────┬─────────────────────┬───────────┘
              │                     │
┌─────────────▼─────────────┐ ┌─────▼────────────────┐
│ Python / local MCP tools  │ │ TypeScript MCP tools │
│ stdio / Streamable HTTP   │ │ Node/Bun/Deno server │
└─────────────┬─────────────┘ └─────┬────────────────┘
              │                     │
        SaaS APIs, DBs, Web, Files, internal services
```

**Merksatz:** Der Agent darf denken. Der Harness muss kontrollieren.

---

# 2. Brauchst du etwas Spezielles für TypeScript-Tools?

## Kurze Antwort

**Nein, nicht wenn TypeScript-Tools als MCP-Server laufen.**
Dann ist TypeScript nur die Implementierungssprache des Servers. Dein Python-Harness spricht MCP über `stdio` oder `Streamable HTTP`.

**Ja, wenn der Agent selbst TypeScript-Code schreiben und ausführen soll.**
Dann brauchst du zusätzlich eine JS/TS-Sandbox, zum Beispiel Node/Bun/Deno in einem Container, Cloudflare Workers/Codemode, Firecracker, gVisor, Docker mit starkem Lockdown oder eine andere isolierte Runtime.

Die offizielle TypeScript-SDK-Dokumentation beschreibt, dass das SDK auf Node.js, Bun und Deno läuft und Server-/Client-Libraries, Streamable HTTP, stdio und Auth-Helfer enthält. Für TS-Tools brauchst du also praktisch: Runtime, Paketmanager, Build-Prozess und einen Transport. ([GitHub][2])

## Drei saubere Wege

| Weg                                    |                                                     Wann nutzen | Was du brauchst                                                                             |
| -------------------------------------- | --------------------------------------------------------------: | ------------------------------------------------------------------------------------------- |
| **TS MCP Server über stdio**           |                      lokale Dev-Tools, CLI-Tools, interne Tools | Node.js, `node dist/server.js` oder `tsx src/server.ts`; im Enterprise aber nur allowlisted |
| **TS MCP Server über Streamable HTTP** |                          Produktion, Remote-Tools, Multi-Tenant | Node.js-Service, Auth, Origin-Check, Observability, Gateway                                 |
| **TS Code-Execution / Code Mode**      | Agent soll selbst TS/JS schreiben, Loops/Joins/Filter ausführen | echte JS/TS-Sandbox, Ressourcenlimits, Netzwerkpolicy, Tool-Bridge                          |

Für Produktion würde ich **TS-Tools als Streamable-HTTP-MCP-Server** betreiben und aus Python verbinden. `stdio` ist okay für Dev und lokale, strikt kontrollierte Tools, aber riskant, wenn User oder Prompts die Server-Konfiguration beeinflussen können.

---

# 3. Was aus dem Video wirklich SOTA ist

## Die 8 Muster, die du kombinieren solltest

| Muster                        | Umsetzung im Harness                                                  | Warum                          |
| ----------------------------- | --------------------------------------------------------------------- | ------------------------------ |
| **Tool Groups**               | Nur passende MCP-Gruppen laden, z. B. `research`, `code`, `finance`   | weniger Tool-Definitionen      |
| **Tool Allowlist**            | Pro Agent/Task feste Toolnamen erlauben                               | Sicherheit + Kosten            |
| **Tool Search**               | BM25/Regex/Embedding-Suche über Tool-Katalog                          | kein Prompt mit 500 Schemas    |
| **Progressive Disclosure**    | Level 1 Server, Level 2 Tool-Summary, Level 3 Schema                  | Agent sieht nur, was nötig ist |
| **Code Execution**            | Agent schreibt Code, Harness führt isoliert aus                       | große Token-Ersparnis          |
| **Programmatic Tool Calling** | Tool-Aufrufe im Code statt jedes Mal LLM-Roundtrip                    | schneller bei Multi-Step       |
| **Output Compaction**         | Markdown strippen, Felder reduzieren, JSON compact, TOON für Tabellen | weniger Output-Tokens          |
| **Policy + Audit**            | Auth, Scopes, tenant isolation, approval gates                        | Enterprise-Pflicht             |

Anthropic beschreibt beim Code-Execution-with-MCP-Muster, dass Tools als Dateien dargestellt werden können, etwa ein Ordner pro Server und eine TypeScript-Datei pro Tool. Der Agent liest dann nur die Tool-Dateien, die er braucht. Im Beispiel sinkt der Kontext von etwa 150.000 auf 2.000 Tokens, also 98,7 Prozent Reduktion. ([anthropic.com][3])

---

# 4. Enterprise-Projektstruktur

So würde ich dein Harness aufsetzen:

```text
enterprise-agent-harness/
  pyproject.toml
  .env.example

  config/
    mcp.servers.yaml
    policies.yaml
    tool-groups.yaml

  src/
    harness/
      __init__.py
      mcp_gateway.py
      tool_catalog.py
      tool_search.py
      policy.py
      redaction.py
      output_compaction.py
      audit.py
      agent_loop.py
      code_exec_bridge.py

  tools/
    ts-mcp-server/
      package.json
      tsconfig.json
      src/server.ts

  sandboxes/
    python/
      Dockerfile
    typescript/
      Dockerfile

  evals/
    tool_selection_eval.py
    prompt_injection_eval.py
    mcp_contract_tests.py
```

---

# 5. `pyproject.toml`

```toml
[project]
name = "enterprise-agent-harness"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "mcp[cli]>=1.0.0",
  "anthropic>=0.52.0",
  "httpx>=0.27.0",
  "pydantic>=2.7.0",
  "pyyaml>=6.0.1",
  "rank-bm25>=0.2.2",
  "orjson>=3.10.0",
  "tenacity>=8.3.0",
  "opentelemetry-api>=1.25.0",
  "opentelemetry-sdk>=1.25.0",
]

[tool.uv]
dev-dependencies = [
  "pytest",
  "pytest-asyncio",
  "ruff",
  "mypy",
]
```

Die offizielle Python-SDK-Dokumentation empfiehlt `uv add "mcp[cli]"` oder `pip install "mcp[cli]"`; sie unterstützt Clients und Server, stdio, SSE und Streamable HTTP. ([GitHub][4])

---

# 6. MCP-Server-Konfiguration

## `config/mcp.servers.yaml`

```yaml
servers:
  brightdata_research:
    transport: streamable_http
    url: "https://mcp.brightdata.com/mcp?token=${BRIGHTDATA_API_TOKEN}&groups=research,code"
    allow_tools:
      - search_engine
      - scrape_as_markdown
      - discover
      - web_data_npm_package
      - web_data_pypi_package
    deny_tools:
      - scraping_browser_type_ref
      - scraping_browser_click_ref
    max_result_chars: 12000
    pii_policy: redact_before_model

  local_ts_tools:
    transport: stdio
    command: "node"
    args:
      - "./tools/ts-mcp-server/dist/server.js"
    env:
      NODE_ENV: "production"
    allow_tools:
      - package_lookup
      - repo_file_summary
    max_result_chars: 8000
    pii_policy: redact_before_model

  internal_python_tools:
    transport: streamable_http
    url: "https://mcp.internal.example.com/mcp"
    oauth: true
    allow_tools:
      - customer_lookup
      - ticket_search
      - read_only_crm_summary
    require_approval_for:
      - customer_update
      - send_email
```

Bright Data dokumentiert genau dieses Scoping-Prinzip: Gruppen lassen sich remote über `groups=<group_name>` oder lokal über `GROUPS=<group_name>` aktivieren; einzelne Tools können lokal über `TOOLS` begrenzt werden. ([docs.brightdata.com][5])

---

# 7. Python MCP Gateway

Das ist die zentrale Schicht: verbinden, Tools listen, filtern, ausführen, Ergebnisse kompakt machen.

```python
# src/harness/mcp_gateway.py

from __future__ import annotations

import asyncio
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Literal

import yaml
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


Transport = Literal["stdio", "streamable_http"]


@dataclass(frozen=True)
class ServerConfig:
    name: str
    transport: Transport
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    allow_tools: set[str] | None = None
    deny_tools: set[str] | None = None
    max_result_chars: int = 12000


@dataclass(frozen=True)
class ToolRef:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPConnection:
    def __init__(self, cfg: ServerConfig) -> None:
        self.cfg = cfg
        self._stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "MCPConnection":
        if self.cfg.transport == "stdio":
            if not self.cfg.command:
                raise ValueError(f"{self.cfg.name}: stdio server needs command")

            # SECURITY: command/args must come from trusted config, never directly from user input.
            server_params = StdioServerParameters(
                command=self.cfg.command,
                args=self.cfg.args or [],
                env=self.cfg.env or {},
            )
            read, write = await self._stack.enter_async_context(stdio_client(server_params))

        elif self.cfg.transport == "streamable_http":
            if not self.cfg.url:
                raise ValueError(f"{self.cfg.name}: streamable_http server needs url")

            read, write, _ = await self._stack.enter_async_context(
                streamable_http_client(expand_env(self.cfg.url))
            )
        else:
            raise ValueError(f"Unsupported transport: {self.cfg.transport}")

        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._stack.aclose()

    async def list_tools(self) -> list[ToolRef]:
        assert self.session is not None
        response = await self.session.list_tools()
        out: list[ToolRef] = []

        for tool in response.tools:
            name = tool.name

            if self.cfg.allow_tools and name not in self.cfg.allow_tools:
                continue
            if self.cfg.deny_tools and name in self.cfg.deny_tools:
                continue

            schema = tool.inputSchema or {"type": "object", "properties": {}}
            out.append(
                ToolRef(
                    server=self.cfg.name,
                    name=name,
                    description=tool.description or "",
                    input_schema=schema,
                )
            )

        return out

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        assert self.session is not None

        if self.cfg.allow_tools and name not in self.cfg.allow_tools:
            raise PermissionError(f"Tool not allowed: {self.cfg.name}.{name}")
        if self.cfg.deny_tools and name in self.cfg.deny_tools:
            raise PermissionError(f"Tool denied: {self.cfg.name}.{name}")

        result = await self.session.call_tool(name, arguments=arguments)
        return normalize_tool_result(result, max_chars=self.cfg.max_result_chars)


class MCPGateway:
    def __init__(self, configs: list[ServerConfig]) -> None:
        self.configs = configs
        self.connections: dict[str, MCPConnection] = {}

    async def __aenter__(self) -> "MCPGateway":
        for cfg in self.configs:
            conn = MCPConnection(cfg)
            self.connections[cfg.name] = await conn.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        for conn in reversed(list(self.connections.values())):
            await conn.__aexit__(exc_type, exc, tb)

    async def catalog(self) -> list[ToolRef]:
        tools: list[ToolRef] = []
        for conn in self.connections.values():
            tools.extend(await conn.list_tools())
        return tools

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if server not in self.connections:
            raise KeyError(f"Unknown server: {server}")
        return await self.connections[server].call_tool(tool, arguments)


def normalize_tool_result(result: Any, max_chars: int) -> dict[str, Any]:
    """
    Converts MCP CallToolResult into a compact dict.
    Keep structuredContent if present; otherwise collect text blocks.
    """
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return {"structured": structured}

    texts: list[str] = []
    for block in getattr(result, "content", []) or []:
        if isinstance(block, types.TextContent):
            texts.append(block.text)

    text = "\n".join(texts)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"

    return {"text": text}


def expand_env(value: str) -> str:
    for key, val in os.environ.items():
        value = value.replace("${" + key + "}", val)
    return value


def load_server_configs(path: str) -> list[ServerConfig]:
    raw = yaml.safe_load(open(path, "r", encoding="utf-8"))
    configs: list[ServerConfig] = []

    for name, cfg in raw["servers"].items():
        configs.append(
            ServerConfig(
                name=name,
                transport=cfg["transport"],
                url=cfg.get("url"),
                command=cfg.get("command"),
                args=cfg.get("args"),
                env=cfg.get("env"),
                allow_tools=set(cfg.get("allow_tools", [])) or None,
                deny_tools=set(cfg.get("deny_tools", [])) or None,
                max_result_chars=cfg.get("max_result_chars", 12000),
            )
        )

    return configs


async def demo() -> None:
    configs = load_server_configs("config/mcp.servers.yaml")

    async with MCPGateway(configs) as gateway:
        tools = await gateway.catalog()
        for tool in tools:
            print(f"{tool.server}.{tool.name}: {tool.description[:120]}")


if __name__ == "__main__":
    asyncio.run(demo())
```

Die Python-SDK-Beispiele zeigen denselben Kern: `ClientSession`, `stdio_client`, `streamable_http_client`, `session.initialize()`, `session.list_tools()` und `session.call_tool()`. ([GitHub][4])

---

# 8. Tool Search statt alle Schemas laden

## `src/harness/tool_search.py`

```python
# src/harness/tool_search.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi

from harness.mcp_gateway import ToolRef


@dataclass(frozen=True)
class SearchResult:
    score: float
    tool: ToolRef


class ToolSearchIndex:
    def __init__(self, tools: list[ToolRef]) -> None:
        self.tools = tools
        self.documents = [self._doc(t) for t in tools]
        self.tokenized = [self._tokenize(d) for d in self.documents]
        self.bm25 = BM25Okapi(self.tokenized)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        scores = self.bm25.get_scores(self._tokenize(query))

        ranked = sorted(
            zip(scores, self.tools),
            key=lambda x: float(x[0]),
            reverse=True,
        )

        return [
            SearchResult(score=float(score), tool=tool)
            for score, tool in ranked[:limit]
            if score > 0
        ]

    def summary_for_model(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Level 2 disclosure:
        Give the model only name + short description.
        Keep full schema hidden until selected.
        """
        results = self.search(query, limit=limit)
        return [
            {
                "server": r.tool.server,
                "name": r.tool.name,
                "description": r.tool.description[:300],
                "score": round(r.score, 3),
            }
            for r in results
        ]

    def full_schema(self, server: str, name: str) -> dict[str, Any]:
        """
        Level 3 disclosure:
        Return schema only when the model selected a concrete tool.
        """
        for tool in self.tools:
            if tool.server == server and tool.name == name:
                return {
                    "server": tool.server,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }

        raise KeyError(f"No such tool: {server}.{name}")

    @staticmethod
    def _doc(tool: ToolRef) -> str:
        schema_text = " ".join((tool.input_schema or {}).get("properties", {}).keys())
        return f"{tool.server} {tool.name} {tool.description} {schema_text}"

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return (
            text.lower()
            .replace("_", " ")
            .replace("-", " ")
            .replace(".", " ")
            .split()
        )
```

Das entspricht dem Prinzip der Anthropic Tool Search: nicht alle Tools upfront laden, sondern über Regex/BM25 suchen und nur 3–5 relevante Tool-Referenzen expandieren. Anthropic nennt als Motivation unter anderem etwa 55k Tokens Tool-Definitionen in typischen Multi-Server-Setups und mehr als 85 Prozent Reduktion durch Tool Search; außerdem sinkt Tool-Selection-Accuracy deutlich ab etwa 30–50 verfügbaren Tools. ([platform.claude.com][6])

---

# 9. Progressive Disclosure für den Agent

Der Agent sollte nicht sofort alle Input-Schemas sehen. Ich würde drei Ebenen nutzen:

```text
Level 1:
  "Du hast Zugriff auf diese Server: brightdata_research, local_ts_tools, internal_python_tools"

Level 2:
  Nach Suchanfrage:
  "Diese 5 Tools passen: server.tool, Kurzbeschreibung"

Level 3:
  Erst nach Auswahl:
  vollständiges Input-Schema genau dieses Tools
```

Beispiel-Prompt an den Planner:

```text
You are an enterprise agent planner.

You do not know all tools upfront.
First call search_tools(query) when external information or actions are needed.
Only request full_schema(server, tool) after choosing a specific tool.
Do not call tools outside the returned schema.
For large or repeated operations, prefer execute_code_plan over repeated direct tool calls.
For write operations, request approval unless policy says otherwise.
```

---

# 10. Anthropic Tool Search direkt nutzen

Wenn du Claude API nutzt, kannst du Anthropic Tool Search serverseitig aktivieren:

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    messages=[
        {"role": "user", "content": "Find current npm and PyPI info for the MCP SDKs."}
    ],
    tools=[
        {
            "type": "tool_search_tool_bm25_20251119",
            "name": "tool_search_tool_bm25",
        },
        {
            "name": "web_data_npm_package",
            "description": "Read structured npm package data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "package": {"type": "string"}
                },
                "required": ["package"],
            },
            "defer_loading": True,
        },
        {
            "name": "web_data_pypi_package",
            "description": "Read structured PyPI package data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "package": {"type": "string"}
                },
                "required": ["package"],
            },
            "defer_loading": True,
        },
    ],
)
```

Die aktuelle Anthropic-Doku nennt zwei Varianten: Regex und BM25. Tools mit `defer_loading: true` werden nicht initial in den Prompt geladen, sondern erst über Tool Search expandiert. ([platform.claude.com][6])

---

# 11. Programmatic Tool Calling

Für Anthropic ist das aktuell ein eigener Pfad: Claude schreibt Code, ruft Tools als Funktionen auf, und Zwischenresultate landen nicht im Modellkontext. Das ist besonders stark bei Multi-Step-Workflows, Filtern, Aggregationen und vielen ähnlichen Tool-Aufrufen. ([platform.claude.com][7])

## Beispiel

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=4096,
    messages=[
        {
            "role": "user",
            "content": (
                "Check package metadata for 20 packages and return only packages "
                "whose latest release is older than 90 days."
            ),
        }
    ],
    tools=[
        {
            "type": "code_execution_20260120",
            "name": "code_execution",
        },
        {
            "name": "package_metadata",
            "description": (
                "Return package metadata as JSON string. "
                "Output fields: name, version, released_at, registry."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "registry": {"type": "string", "enum": ["npm", "pypi"]},
                    "package": {"type": "string"},
                },
                "required": ["registry", "package"],
            },
            "allowed_callers": ["code_execution_20260120"],
        },
    ],
)
```

Wichtig: Anthropic dokumentiert aktuell, dass **Tools aus einem MCP Connector nicht programmatic callable sind**; dafür müsstest du MCP-Tools entweder als eigene First-Party-Tools wrappen oder eine eigene Sandbox/Bridge bauen. ([platform.claude.com][7])

---

# 12. MCP-Tools als First-Party-Tools wrappen

Wenn du MCP-Tools programmatic callable machen willst, ist der pragmatische Trick:

```text
MCP Tool
  ↓
Python wrapper function
  ↓
Anthropic custom tool with allowed_callers=["code_execution_20260120"]
  ↓
Claude code execution
```

Konzeptuell:

```python
# src/harness/anthropic_tools.py

from __future__ import annotations

from harness.mcp_gateway import MCPGateway


def anthropic_tool_def_for_mcp(server: str, tool: str, schema: dict) -> dict:
    return {
        "name": f"mcp__{server}__{tool}",
        "description": f"Call MCP tool {server}.{tool}. Returns compact JSON.",
        "input_schema": schema,
        "allowed_callers": ["code_execution_20260120"],
    }


async def execute_wrapped_mcp_tool(
    gateway: MCPGateway,
    wrapped_name: str,
    arguments: dict,
) -> str:
    # wrapped_name format: mcp__server__tool
    _, server, tool = wrapped_name.split("__", 2)

    result = await gateway.call(
        server=server,
        tool=tool,
        arguments=arguments,
    )

    # Return string because programmatic tool results are passed back as strings.
    import orjson
    return orjson.dumps(result).decode("utf-8")
```

Das ist nicht so elegant wie native MCP programmatic calling, aber aktuell der zuverlässigste Enterprise-Weg, wenn du Claude API + MCP + Programmatic Tool Calling kombinieren willst.

---

# 13. TypeScript MCP Server

## `tools/ts-mcp-server/package.json`

```json
{
  "name": "enterprise-ts-mcp-server",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "tsx src/server.ts",
    "build": "tsc -p tsconfig.json",
    "start": "node dist/server.js"
  },
  "dependencies": {
    "@modelcontextprotocol/server": "^1.29.0",
    "zod": "^4.0.0"
  },
  "devDependencies": {
    "tsx": "^4.19.0",
    "typescript": "^5.6.0"
  }
}
```

## `tools/ts-mcp-server/src/server.ts`

```ts
import { McpServer, StdioServerTransport } from "@modelcontextprotocol/server";
import * as z from "zod/v4";

const server = new McpServer({
  name: "enterprise-ts-tools",
  version: "0.1.0",
});

server.registerTool(
  "package_lookup",
  {
    title: "Package Lookup",
    description: "Return minimal package information for npm-style packages.",
    inputSchema: z.object({
      packageName: z.string(),
    }),
    outputSchema: z.object({
      packageName: z.string(),
      registry: z.string(),
      status: z.string(),
    }),
  },
  async ({ packageName }) => {
    const output = {
      packageName,
      registry: "npm",
      status: "placeholder-demo",
    };

    return {
      content: [{ type: "text", text: JSON.stringify(output) }],
      structuredContent: output,
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

Die TypeScript-SDK-Server-Doku beschreibt genau diese drei Schritte: `McpServer` erstellen und Tools/Resources/Prompts registrieren, Transport wählen, dann `server.connect(transport)`. ([GitHub][8])

---

# 14. TypeScript als Streamable HTTP statt stdio

Für Produktion würde ich eher HTTP nehmen:

```ts
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/server";
import { NodeStreamableHTTPServerTransport } from "@modelcontextprotocol/node";
import * as z from "zod/v4";

const server = new McpServer({
  name: "enterprise-ts-http-tools",
  version: "0.1.0",
});

server.registerTool(
  "repo_file_summary",
  {
    description: "Summarize a known repository file.",
    inputSchema: z.object({
      repo: z.string(),
      path: z.string(),
    }),
  },
  async ({ repo, path }) => ({
    content: [
      {
        type: "text",
        text: JSON.stringify({
          repo,
          path,
          summary: "placeholder-demo",
        }),
      },
    ],
  })
);

const transport = new NodeStreamableHTTPServerTransport({
  sessionIdGenerator: () => randomUUID(),
});

await server.connect(transport);
```

Streamable HTTP ist der aktuelle Standardtransport für Remote-Server. Die Spezifikation sagt unter anderem: ein MCP-Endpunkt unterstützt POST und GET, Clients müssen JSON und SSE unterstützen, und bei Streamable HTTP müssen Server den `Origin`-Header validieren, lokal nur an `localhost` binden und Auth für Verbindungen implementieren. ([Model Context Protocol][9])

---

# 15. Code-Execution mit MCP als Dateisystem

Das Muster aus dem Video kannst du in deinem Harness selbst erzeugen.

## Automatisch generierte Tool-Dateien

```text
.generated_tools/
  brightdata_research/
    search_engine.ts
    scrape_as_markdown.ts
    discover.ts
    index.ts
  local_ts_tools/
    package_lookup.ts
    repo_file_summary.ts
    index.ts
```

## Beispiel generierte Datei

```ts
// .generated_tools/brightdata_research/search_engine.ts

import { callMcpTool } from "../../runtime/mcp-client";

export type SearchEngineInput = {
  query: string;
  engine?: "google" | "bing" | "yandex";
};

export type SearchEngineOutput = {
  results: Array<{
    title: string;
    url: string;
    snippet?: string;
  }>;
};

export async function search_engine(
  input: SearchEngineInput
): Promise<SearchEngineOutput> {
  return callMcpTool<SearchEngineOutput>(
    "brightdata_research",
    "search_engine",
    input
  );
}
```

## Agent-Code-Beispiel

```ts
import { search_engine } from "./.generated_tools/brightdata_research/search_engine";
import { scrape_as_markdown } from "./.generated_tools/brightdata_research/scrape_as_markdown";

const search = await search_engine({
  query: "model context protocol 2026 roadmap enterprise readiness",
  engine: "google"
});

const topUrls = search.results.slice(0, 3).map((r) => r.url);

const pages = [];
for (const url of topUrls) {
  const page = await scrape_as_markdown({ url });
  pages.push({ url, text: page.markdown.slice(0, 4000) });
}

console.log(JSON.stringify({
  inspected: pages.length,
  urls: pages.map((p) => p.url)
}));
```

Das ist der Kern der 98-Prozent-Idee: Der Agent sieht nicht 60 Tool-Schemas und 10.000 Zeilen Rohdaten, sondern schreibt Code, filtert lokal und gibt nur eine knappe Zusammenfassung zurück. Anthropic hebt zusätzlich hervor, dass Zwischenresultate in der Ausführungsumgebung bleiben und nur explizit geloggte oder zurückgegebene Daten ins Modell gelangen. ([anthropic.com][3])

---

# 16. Eigene TS/JS-Sandbox

Wenn du **wirklich TS-Code vom Agent ausführen lassen willst**, brauchst du ein getrenntes Execution-System.

## Minimaler TS-Sandbox-Dockerfile

```dockerfile
# sandboxes/typescript/Dockerfile
FROM node:22-slim

RUN useradd -m sandbox
USER sandbox
WORKDIR /workspace

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev || npm install --omit=dev

COPY runtime ./runtime

ENV NODE_ENV=production
CMD ["node", "runtime/runner.js"]
```

## Sandbox-Regeln

```text
- kein Root
- read-only filesystem, außer /workspace/tmp
- CPU-Limit
- Memory-Limit
- Timeout pro Run
- Netzwerk standardmäßig aus
- nur explizite Tool-Bridge darf raus
- Secrets nie in Sandbox-Env
- Tool-Resultate validieren
- stdout begrenzen
```

Cloudflare beschreibt bei Codemode ein verwandtes Muster: TypeScript-Typdefinitionen aus Tools generieren, dem LLM ein einziges „write code“-Tool geben und den generierten JavaScript-Code in einem isolierten Worker ausführen. Cloudflare markiert Codemode allerdings als experimentell. ([Cloudflare Docs][10])

---

# 17. Output Compaction

## `src/harness/output_compaction.py`

````python
# src/harness/output_compaction.py

from __future__ import annotations

import re
from typing import Any

import orjson


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_json(data: Any, keep_keys: set[str] | None = None) -> str:
    if keep_keys is not None:
        data = project_keys(data, keep_keys)
    return orjson.dumps(data).decode("utf-8")


def project_keys(data: Any, keep_keys: set[str]) -> Any:
    if isinstance(data, dict):
        return {
            k: project_keys(v, keep_keys)
            for k, v in data.items()
            if k in keep_keys or isinstance(v, (dict, list))
        }
    if isinstance(data, list):
        return [project_keys(x, keep_keys) for x in data]
    return data


def to_flat_rows(items: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    return [{k: item.get(k) for k in keys} for item in items]
````

## Wann TOON?

TOON ist sinnvoll bei flachen, uniformen Arrays, etwa Tabellen, Produktlisten, SERPs, Logs oder einfache Records. Bright Data nennt 30–60 Prozent Token-Reduktion gegenüber JSON, warnt aber, dass TOON bei tief verschachtelten und uneinheitlichen Daten wenig bringt; bei Bright-Data-MCP-Endpunkten muss man häufig erst flatten. ([docs.brightdata.com][11])

---

# 18. Security: Was du am 29.04.2026 unbedingt beachten musst

## MUST KNOW

### 1. `stdio` niemals aus User-Input konfigurieren

Aktuelle Security-Advisories im April 2026 drehen sich genau um MCP-`stdio`-Konfigurationen, bei denen untrusted Input in `command`/`args` landet und dadurch OS-Kommandos ausgeführt werden können. OX Security beschreibt mehrere Exploit-Familien rund um MCP-STDIO-Konfigurationen und RCE; LiteLLM dokumentierte konkret eine gepatchte Variante, bei der `command` und `args` an `StdioServerParameters` durchgereicht wurden. ([OX Security][12])

**Regel:**

```text
User darf nie command, args, env, cwd oder package name eines stdio-MCP-Servers setzen.
```

Erlaubt ist nur:

```text
server_id = "approved_brightdata"
server_id = "approved_internal_crm"
server_id = "approved_ts_tools"
```

Der Harness mappt dann intern auf eine feste, versionierte, signierte Config.

---

### 2. Streamable HTTP braucht Origin-Check und Auth

Die MCP-Transport-Spezifikation verlangt bei Streamable HTTP Origin-Validation gegen DNS-Rebinding; lokale Server sollen nur an `127.0.0.1` binden, und Auth wird empfohlen. ([Model Context Protocol][9])

**Enterprise-Regel:**

```text
Remote MCP:
  - HTTPS only
  - OAuth / mTLS / signed service token
  - Origin allowlist
  - tenant-aware sessions
  - no bearer tokens in query strings
```

---

### 3. Kein Token Passthrough

MCP-Security-Best-Practices nennen Token Passthrough explizit als Anti-Pattern: Ein MCP-Server soll keine Tokens akzeptieren, die nicht für ihn ausgestellt wurden, und sie nicht einfach an Downstream-APIs weiterreichen. ([Model Context Protocol][13])

**Richtig:**

```text
Client token → MCP server validates audience → MCP server uses own downstream credential / token exchange
```

**Falsch:**

```text
Client gives Google token → MCP server blindly forwards token to Google
```

---

### 4. OAuth mit Resource Indicators

Die aktuelle MCP-Authorization-Spezifikation verlangt Resource Indicators: Der Client muss in Authorization- und Token-Requests das Ziel-Resource angeben; Access Tokens müssen als Bearer im Authorization Header gesendet werden und dürfen nicht in Query Strings landen. ([Model Context Protocol][14])

---

### 5. MCP-Tool-Metadaten sind nicht vertrauenswürdig

Die Spezifikation warnt, dass Tools beliebige Codeausführung repräsentieren und Tool-Beschreibungen/Annotations nicht blind vertraut werden dürfen, sofern sie nicht von einem vertrauenswürdigen Server kommen. ([Model Context Protocol][1])

**Konsequenz:**

```text
Tool descriptions are data, not policy.
Policy lives in your harness.
```

---

# 19. SHOULD KNOW

## 1. MCP 2025-11-25 ist aktuell die relevante Spezifikation

Die Changelog-Seite markiert `2025-11-25` als latest und nennt wichtige Änderungen: OIDC Discovery, inkrementelle Scope-Zustimmung, Tool-Namenshinweise, Sampling mit Tools, OAuth Client ID Metadata Documents, experimentelle Tasks und JSON Schema 2020-12 als Default-Dialekt. ([Model Context Protocol][15])

## 2. Enterprise Readiness ist noch im Ausbau

Die offizielle MCP-Roadmap, zuletzt aktualisiert am 05.03.2026, nennt explizit Lücken bei Audit Trails, Observability, Enterprise-Managed Auth, Gateway/Proxy-Patterns und Configuration Portability. Für Enterprise heißt das: Du brauchst heute selbst ein Governance-Gateway, nicht nur rohe MCP-Clients. ([Model Context Protocol][16])

## 3. Enterprise-Managed Authorization ist wichtig

Die MCP-Extension für Enterprise-Managed Authorization soll zentralen Zugriff über bestehende Identity Provider ermöglichen, statt dass jeder Mitarbeiter jeden MCP-Server einzeln autorisiert. Für Unternehmen ist das der bessere Zielzustand. ([Model Context Protocol][17])

## 4. MCP Apps sind produktionsrelevant

MCP Apps sind seit 26.01.2026 die erste offizielle MCP-Extension; Tools können UI-Komponenten wie Dashboards, Formulare oder Visualisierungen zurückgeben, die in einem sandboxed iframe gerendert werden. Das ist relevant, wenn dein Agent nicht nur Text, sondern Review-/Approval-/Dashboard-Flows braucht. ([Model Context Protocol Blog][18])

---

# 20. GOOD TO KNOW

## 1. Inspector immer in CI/Dev nutzen

Der MCP Inspector ist ein interaktives Tool zum Testen und Debuggen von MCP-Servern. Er kann Tools, Prompts, Resources, Notifications und Tool-Schemas anzeigen und testen. ([Model Context Protocol][19])

Beispiel:

```bash
npx @modelcontextprotocol/inspector node tools/ts-mcp-server/dist/server.js
```

Oder für Python:

```bash
npx @modelcontextprotocol/inspector \
  uv \
  --directory path/to/server \
  run \
  package-name
```

## 2. Bright Data Gruppen direkt nutzen

Für Web-/Research-Agents solltest du Bright Data nicht mit allen Tools laden. Nimm Gruppen und Tool-Allowlists:

```json
{
  "mcpServers": {
    "Bright Data": {
      "command": "npx",
      "args": ["@brightdata/mcp"],
      "env": {
        "API_TOKEN": "<token>",
        "PRO_MODE": "true",
        "GROUPS": "research,code",
        "TOOLS": "search_engine,scrape_as_markdown,discover,web_data_npm_package,web_data_pypi_package"
      }
    }
  }
}
```

Bright Data dokumentiert Rapid/Pro-Modus, 11 Tool-Gruppen und Gruppenaktivierung über URL oder Environment. ([docs.brightdata.com][5])

## 3. Große Results nie roh ans Modell

Für Tabellen:

```text
MCP result → filter → flatten → compact JSON or TOON → model
```

Für Webseiten:

```text
HTML/Markdown → remove nav/ads/footer → extract headings + paragraphs → summarize or cite
```

Für interne Daten:

```text
raw rows → policy filter → PII tokenize/redact → aggregate → model
```

---

# 21. Policy Layer

## `config/policies.yaml`

```yaml
defaults:
  deny_write_tools: true
  max_tool_calls_per_turn: 12
  max_result_chars: 12000
  require_human_approval_for:
    - send_email
    - update_customer
    - delete_record
    - payment
    - deploy
    - browser_click
    - browser_type

servers:
  brightdata_research:
    allowed_domains:
      - "*"
    blocked_domains:
      - "localhost"
      - "127.0.0.1"
      - "169.254.169.254"
      - "10.0.0.0/8"
      - "192.168.0.0/16"

  internal_python_tools:
    allowed_tenants_from_claim: true
    audit_level: full
    pii_policy: tokenize
```

## `src/harness/policy.py`

```python
# src/harness/policy.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    server: str
    tool: str
    arguments: dict[str, Any]
    user_id: str
    tenant_id: str


class PolicyDecision:
    def __init__(self, allow: bool, reason: str, require_approval: bool = False) -> None:
        self.allow = allow
        self.reason = reason
        self.require_approval = require_approval


class PolicyEngine:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def check_tool_call(self, call: ToolCall) -> PolicyDecision:
        dangerous_names = {
            "send_email",
            "update_customer",
            "delete_record",
            "payment",
            "deploy",
            "browser_click",
            "browser_type",
        }

        if call.tool in dangerous_names:
            return PolicyDecision(
                allow=True,
                reason="Tool requires human approval",
                require_approval=True,
            )

        if "url" in call.arguments:
            url = str(call.arguments["url"])
            if self._is_blocked_url(url):
                return PolicyDecision(
                    allow=False,
                    reason=f"Blocked URL target: {url}",
                )

        return PolicyDecision(allow=True, reason="Allowed")

    def _is_blocked_url(self, url: str) -> bool:
        blocked = [
            "localhost",
            "127.0.0.1",
            "169.254.169.254",
            "10.",
            "192.168.",
        ]
        return any(x in url for x in blocked)
```

Das ist bewusst simpel. In Produktion würde ich OPA, Cedar, Zanzibar-artige ReBAC-Regeln oder interne IAM-Policy anschließen.

---

# 22. Agent Loop: direkt vs. code execution

## Entscheidungsmatrix

```python
def should_use_code_execution(
    expected_tool_calls: int,
    expected_rows: int,
    has_sensitive_intermediate_data: bool,
    needs_loop_or_join: bool,
) -> bool:
    if expected_tool_calls >= 3:
        return True
    if expected_rows >= 500:
        return True
    if has_sensitive_intermediate_data:
        return True
    if needs_loop_or_join:
        return True
    return False
```

## Faustregel

```text
1 einfacher Tool Call:
  Direct tool call

3+ Tool Calls:
  Programmatic tool calling / code execution

Viele Zeilen, viele Seiten, viele Profile:
  Code execution + filtering + compact output

Write operation:
  Policy + approval gate
```

Anthropic empfiehlt Programmatic Tool Calling besonders für große Datensätze, Multi-Step-Workflows mit 3+ abhängigen Tool Calls, Filtering/Sorting/Transformation und Fälle, in denen Zwischenresultate nicht das Reasoning beeinflussen sollen. ([platform.claude.com][7])

---

# 23. Was ich in deinem Harness nicht tun würde

```text
Nicht:
  - 100 Tool-Schemas in jeden Prompt laden
  - stdio config aus User-Input erlauben
  - npx irgendein Paket aus Marketplace ungeprüft starten
  - Secrets in Code-Sandbox geben
  - Browser-Tools ohne Approval erlauben
  - Rohes HTML/Markdown direkt ans Modell geben
  - Tool descriptions als Sicherheitsquelle behandeln
  - Write-Tools und Read-Tools gleich behandeln
```

---

# 24. Minimaler erster Build-Plan

## Phase 1: Solider MCP Gateway

Baue zuerst:

```text
- mcp.servers.yaml
- Python MCPGateway
- allowlist/denylist
- catalog()
- call()
- result truncation
- audit log
```

## Phase 2: Tool Search

Dann:

```text
- BM25 Tool Index
- search_tools(query)
- full_schema(server, tool)
- nie alle Schemas in den Prompt
```

## Phase 3: Enterprise Policy

Dann:

```text
- tenant-aware auth
- approval gates
- SSRF blocking
- no user-controlled stdio
- secrets isolation
- PII redaction/tokenization
```

## Phase 4: Code Execution

Dann:

```text
- Python code execution for programmatic tool calling
- optional TS sandbox if agent should write TS/JS
- generated tool wrappers
- stdout/stderr/result limits
```

## Phase 5: Optimization

Dann:

```text
- JSON compaction
- Markdown stripping
- TOON for flat arrays
- prompt caching
- evals for tool selection
```

---

# 25. Meine harte Empfehlung

Für dein Enterprise-Harness würde ich diesen Standard setzen:

```text
Production default:
  Streamable HTTP MCP servers
  OAuth / enterprise IdP
  tool groups
  tool allowlists
  BM25/embedding tool search
  progressive schema loading
  code execution only in sandbox
  no user-supplied stdio config
  audit everything

Dev/local:
  stdio allowed
  but only from trusted checked-in config
  never from prompt/user/marketplace input
```

Und für TypeScript:

```text
TS tools:
  run as MCP server via Node/Bun/Deno
  expose over Streamable HTTP for production
  connect from Python using MCP client

TS code execution:
  only with separate JS/TS sandbox
  no secrets
  no default network
  tool bridge allowlisted
```

Das ist die robuste SOTA-Variante: MCP als protocol layer, Python als governance/control plane, TypeScript als tool implementation/runtime, und Code Execution als isolierte compute plane.

[1]: https://modelcontextprotocol.io/specification/2025-11-25 "Specification - Model Context Protocol"
[2]: https://github.com/modelcontextprotocol/typescript-sdk "GitHub - modelcontextprotocol/typescript-sdk: The official TypeScript SDK for Model Context Protocol servers and clients · GitHub"
[3]: https://www.anthropic.com/engineering/code-execution-with-mcp "Code execution with MCP: building more efficient AI agents \ Anthropic"
[4]: https://github.com/modelcontextprotocol/python-sdk "GitHub - modelcontextprotocol/python-sdk: The official Python SDK for Model Context Protocol servers and clients · GitHub"
[5]: https://docs.brightdata.com/ai/mcp-server/tools "Tools - Bright Data Docs"
[6]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool "Tool search tool - Claude API Docs"
[7]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling "Programmatic tool calling - Claude API Docs"
[8]: https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md "typescript-sdk/docs/server.md at main · modelcontextprotocol/typescript-sdk · GitHub"
[9]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Transports - Model Context Protocol"
[10]: https://developers.cloudflare.com/agents/api-reference/codemode/ "Codemode · Cloudflare Agents docs"
[11]: https://docs.brightdata.com/ai/mcp-server/toon "TOON Format - Bright Data Docs"
[12]: https://www.ox.security/blog/mcp-supply-chain-advisory-rce-vulnerabilities-across-the-ai-ecosystem/?utm_source=chatgpt.com "MCP STDIO Command Injection: Full Vulnerability Advisory"
[13]: https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices "Security Best Practices - Model Context Protocol"
[14]: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization "Authorization - Model Context Protocol"
[15]: https://modelcontextprotocol.io/specification/2025-11-25/changelog "Key Changes - Model Context Protocol"
[16]: https://modelcontextprotocol.io/development/roadmap "Roadmap - Model Context Protocol"
[17]: https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization "Enterprise-Managed Authorization - Model Context Protocol"
[18]: https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/ "MCP Apps - Bringing UI Capabilities To MCP Clients | Model Context Protocol Blog"
[19]: https://modelcontextprotocol.io/docs/tools/inspector "MCP Inspector - Model Context Protocol"


