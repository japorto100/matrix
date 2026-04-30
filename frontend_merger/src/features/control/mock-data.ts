// Control Surface — mock data for Slice 5 + 6
// Replace with real API calls in Slice 5/6 backend phase.

import type {
	A2ADelegation,
	AgentOpsReadModel,
	AgentRole,
	AuditEvent,
	ContextInspectorResponse,
	EnvVar,
	LlmProvider,
	MatrixWidgetApprovalItem,
	McpServer,
	ModelRouting,
	OverviewSnapshot,
	PermissionCell,
	PromptCacheReadModel,
	ReportArtifact,
	SandboxRun,
	SecurityPosture,
	SemanticCatalogResponse,
	ServiceStatus,
	Session,
	Skill,
	ToolCategory,
	ToolDefinition,
	TradingRole,
	UtilityModel,
} from "./types";

// ─── Trading Roles (mirror exec-12 consent_policy.yaml) ────────────────────

// IMPORTANT: role ids MUST match backend agent/roles.py TradingRole enum.
// Backend is the source of truth (inspired by TauricResearch/TradingAgents).
export const mockAgentRoles: AgentRole[] = [
	{
		id: "fundamentals_analyst",
		display_name: "Fundamentals Analyst",
		system_prompt:
			"You are a Fundamentals Analyst. Analyze company financials: balance sheets, income statements, cash flow, earnings reports, and valuation metrics.",
		allowed_tools: [
			"get_portfolio_summary",
			"get_chart_state",
			"save_memory",
			"load_memory",
			"sandbox_execute",
		],
		memory_access: "read_write",
		approval_required: false,
		is_default: true,
	},
	{
		id: "sentiment_analyst",
		display_name: "Sentiment Analyst",
		system_prompt:
			"You are a Sentiment Analyst. Analyze market sentiment from news, social media, analyst ratings, and market indicators (VIX, put/call ratios, fund flows).",
		allowed_tools: ["get_chart_state", "save_memory", "load_memory"],
		memory_access: "read_write",
		approval_required: false,
		is_default: true,
	},
	{
		id: "technical_analyst",
		display_name: "Technical Analyst",
		system_prompt:
			"You are a Technical Analyst. Analyze price charts, patterns, and indicators. Use RSI, MACD, moving averages, Bollinger Bands, support/resistance.",
		allowed_tools: ["get_chart_state", "save_memory", "load_memory", "sandbox_execute"],
		memory_access: "read_write",
		approval_required: false,
		is_default: true,
	},
	{
		id: "researcher",
		display_name: "Researcher",
		system_prompt:
			"You are a Research Analyst. Synthesize findings from fundamental, sentiment, and technical analysis. Present balanced bull and bear arguments.",
		allowed_tools: [
			"get_chart_state",
			"get_portfolio_summary",
			"save_memory",
			"load_memory",
			"sandbox_execute",
			"sandbox_browser",
		],
		memory_access: "read_write",
		approval_required: false,
		is_default: false,
		updated_at: "2026-04-05T10:23:00Z",
		updated_by: "local",
	},
	{
		id: "trader",
		display_name: "Trader",
		system_prompt:
			"You are a Trader. Based on the research summary, make actionable trading decisions. Define entry/exit points, position size, and timeframe.",
		allowed_tools: [
			"get_chart_state",
			"set_chart_state",
			"get_portfolio_summary",
			"save_memory",
			"load_memory",
		],
		memory_access: "read_write",
		approval_required: true,
		is_default: true,
	},
	{
		id: "risk_manager",
		display_name: "Risk Manager",
		system_prompt:
			"You are a Risk Manager. Evaluate proposed trades for risk exposure. Check position sizing, portfolio concentration, correlation risk, drawdown limits.",
		allowed_tools: ["get_portfolio_summary", "save_memory", "load_memory"],
		memory_access: "read",
		approval_required: true,
		is_default: true,
	},
];

// ─── Tool Categories + Permission Matrix (D2 D2.1) ─────────────────────────

export const mockToolCategories: ToolCategory[] = [
	{
		id: "market_data",
		display_name: "Market Data",
		tools: ["get_quote", "search_news", "yield_curves", "fred_data"],
	},
	{
		id: "trading",
		display_name: "Trading",
		tools: ["place_order", "cancel_order", "get_order_status"],
	},
	{
		id: "risk",
		display_name: "Risk Mgmt",
		tools: ["calc_var", "stress_test", "halt_trading", "get_positions"],
	},
	{
		id: "memory",
		display_name: "Memory",
		tools: ["memory_retain", "memory_recall", "memory_reflect"],
	},
	{
		id: "sandbox",
		display_name: "Sandbox Exec",
		tools: ["sandbox_python", "sandbox_bash", "sandbox_browser"],
	},
	{
		id: "system",
		display_name: "System",
		tools: ["read_audit_log", "flag_event", "list_files"],
	},
	{
		id: "a2a",
		display_name: "A2A Delegate",
		tools: ["delegate_to_agent", "wait_for_agent"],
	},
];

export const mockPermissions: PermissionCell[] = (() => {
	const cells: PermissionCell[] = [];
	const matrix: Record<string, Record<TradingRole, "auto" | "inform" | "confirm" | "deny">> = {
		market_data: {
			fundamentals_analyst: "auto",
			researcher: "auto",
			risk_manager: "auto",
			sentiment_analyst: "auto",
			trader: "inform",
			technical_analyst: "auto",
		},
		trading: {
			fundamentals_analyst: "deny",
			researcher: "confirm",
			risk_manager: "deny",
			sentiment_analyst: "deny",
			trader: "confirm",
			technical_analyst: "deny",
		},
		risk: {
			fundamentals_analyst: "inform",
			researcher: "auto",
			risk_manager: "auto",
			sentiment_analyst: "inform",
			trader: "inform",
			technical_analyst: "auto",
		},
		memory: {
			fundamentals_analyst: "auto",
			researcher: "auto",
			risk_manager: "auto",
			sentiment_analyst: "auto",
			trader: "inform",
			technical_analyst: "auto",
		},
		sandbox: {
			fundamentals_analyst: "confirm",
			researcher: "confirm",
			risk_manager: "deny",
			sentiment_analyst: "confirm",
			trader: "deny",
			technical_analyst: "deny",
		},
		system: {
			fundamentals_analyst: "deny",
			researcher: "inform",
			risk_manager: "auto",
			sentiment_analyst: "deny",
			trader: "deny",
			technical_analyst: "auto",
		},
		a2a: {
			fundamentals_analyst: "inform",
			researcher: "auto",
			risk_manager: "inform",
			sentiment_analyst: "inform",
			trader: "deny",
			technical_analyst: "inform",
		},
	};
	const overrides = new Set([
		"researcher:trading",
		"risk_manager:risk",
		"technical_analyst:system",
	]);
	for (const cat of Object.keys(matrix)) {
		for (const role of Object.keys(matrix[cat]!) as TradingRole[]) {
			cells.push({
				role_id: role,
				category_id: cat,
				level: matrix[cat]![role]!,
				is_overridden: overrides.has(`${role}:${cat}`),
			});
		}
	}
	return cells;
})();

// ─── Skills (3 Tier from exec-10) ──────────────────────────────────────────

export const mockSkills: Skill[] = [
	{
		id: "skill_001",
		name: "stock-screener-multifactor",
		tier: "global",
		description: "Multi-factor screen: P/E + momentum + earnings revisions + insider buying",
		generation: 4,
		last_used_at: "2026-04-07T08:32:00Z",
		enabled: true,
		source: "builtin",
		body_preview:
			"# Multi-Factor Stock Screener\n\nApplies a 4-factor model to filter S&P 500 universe...",
	},
	{
		id: "skill_002",
		name: "news-sentiment-extractor",
		tier: "global",
		description: "Extract sentiment + entities + event types from financial news",
		generation: 7,
		last_used_at: "2026-04-07T09:11:00Z",
		enabled: true,
		source: "builtin",
		body_preview:
			"# News Sentiment Extractor\n\nPipeline: NER → sentiment → event classification...",
	},
	{
		id: "skill_003",
		name: "claude-research-deep",
		tier: "team",
		description: "Multi-round research using Claude with tool use",
		generation: 2,
		last_used_at: "2026-04-06T15:42:00Z",
		enabled: true,
		source: "github",
		github_url: "https://github.com/anthropics/skills/research-deep",
		body_preview: "# Deep Research Skill\n\nIterative research with tool use, citation tracking...",
	},
	{
		id: "skill_004",
		name: "btc-onchain-flow",
		tier: "personal",
		description: "Custom: BTC onchain flow analysis (whale movements, exchange flows)",
		generation: 1,
		last_used_at: "2026-04-07T07:05:00Z",
		enabled: true,
		source: "local",
		body_preview: "# BTC Onchain Flow Analyzer\n\nMonitors whale wallets + exchange inflows...",
	},
	{
		id: "skill_005",
		name: "sec-13f-tracker",
		tier: "personal",
		description: "Track 13F filings of large funds + change deltas",
		generation: 3,
		enabled: false,
		source: "local",
		body_preview: "# SEC 13F Tracker\n\nFetches quarterly 13F filings...",
	},
];

// ─── Sandbox Runs ──────────────────────────────────────────────────────────

export const mockSandboxRuns: SandboxRun[] = [
	{
		id: "sb_001",
		user_id: "local",
		role: "fundamentals_analyst",
		tool_name: "sandbox_python",
		code_preview:
			"import yfinance as yf\ntickers = ['AAPL', 'MSFT', 'NVDA']\nfor t in tickers:\n  print(yf.Ticker(t).info['trailingPE'])",
		status: "completed",
		started_at: "2026-04-07T09:15:23Z",
		completed_at: "2026-04-07T09:15:31Z",
		duration_ms: 8200,
		stdout_preview: "29.4\n34.2\n62.1\n",
		exit_code: 0,
	},
	{
		id: "sb_002",
		user_id: "local",
		role: "sentiment_analyst",
		tool_name: "sandbox_python",
		code_preview:
			"import pandas as pd\nimport requests\nfred_data = requests.get('https://api.fred.stlouisfed.org/...').json()\n# parse + plot",
		status: "running",
		started_at: "2026-04-07T09:32:10Z",
	},
	{
		id: "sb_003",
		user_id: "local",
		role: "researcher",
		tool_name: "sandbox_python",
		code_preview:
			"# Stress test portfolio under -20% scenario\nimport numpy as np\npositions = load_positions()\n...",
		status: "failed",
		started_at: "2026-04-07T08:42:00Z",
		completed_at: "2026-04-07T08:42:14Z",
		duration_ms: 14000,
		stderr_preview: "FileNotFoundError: 'positions.csv' not in sandbox",
		exit_code: 1,
	},
	{
		id: "sb_004",
		user_id: "local",
		role: "fundamentals_analyst",
		tool_name: "sandbox_browser",
		code_preview: "// Playwright: scrape earnings call transcript from fool.com",
		status: "completed",
		started_at: "2026-04-07T07:55:00Z",
		completed_at: "2026-04-07T07:55:42Z",
		duration_ms: 42100,
		stdout_preview: "Captured 8412 words from transcript",
		exit_code: 0,
	},
	{
		id: "sb_005",
		user_id: "local",
		role: "risk_manager",
		tool_name: "sandbox_python",
		code_preview:
			"# Quick VaR calc\nimport numpy as np\nreturns = ...\nvar_95 = np.percentile(returns, 5)",
		status: "timeout",
		started_at: "2026-04-06T23:11:00Z",
		completed_at: "2026-04-06T23:21:00Z",
		duration_ms: 600000,
	},
];

// ─── Tools Registry ────────────────────────────────────────────────────────

export const mockTools: ToolDefinition[] = [
	{
		id: "tool_search_news",
		name: "search_news",
		type: "builtin",
		description: "Search financial news from major outlets (Bloomberg, Reuters, FT, WSJ)",
		provider: "matrix-builtin",
		input_schema_summary: "{ query: str, limit: int = 10, sources?: str[] }",
		categories: ["market_data"],
		last_called_at: "2026-04-07T09:34:00Z",
		call_count_24h: 142,
		avg_latency_ms: 320,
		enabled: true,
	},
	{
		id: "tool_get_quote",
		name: "get_quote",
		type: "builtin",
		description: "Real-time stock quote (last, bid, ask, volume, change)",
		provider: "matrix-builtin",
		input_schema_summary: "{ symbol: str }",
		categories: ["market_data"],
		last_called_at: "2026-04-07T09:35:12Z",
		call_count_24h: 891,
		avg_latency_ms: 45,
		enabled: true,
	},
	{
		id: "tool_semantic_lookup",
		name: "semantic_lookup",
		type: "builtin",
		description:
			"Resolve Matrix semantic terms and governed metric definitions before metric-sensitive answers",
		summary:
			"Authoritative semantic lookup with provenance, freshness, ambiguity handling and raw SQL disabled.",
		provider: "matrix-builtin",
		input_schema_summary: "{ phrase: str, tenant_id?: str, include_metric_plan?: bool = true }",
		categories: ["semantic", "metrics", "governance"],
		group: "semantic",
		risk: "low",
		approval: "auto",
		progressive_disclosure_level: 1,
		policy_reasons: ["raw-sql-disabled", "authoritative-definition"],
		last_called_at: "2026-04-29T19:00:00Z",
		call_count_24h: 0,
		avg_latency_ms: 12,
		enabled: true,
	},
	{
		id: "tool_calc_var",
		name: "calc_var",
		type: "builtin",
		description: "Calculate Value-at-Risk for a portfolio (parametric, historical, or MC)",
		provider: "matrix-builtin",
		input_schema_summary:
			"{ positions: PositionList, method: 'parametric'|'historical'|'mc', confidence: float = 0.95 }",
		categories: ["risk"],
		last_called_at: "2026-04-07T08:12:00Z",
		call_count_24h: 23,
		avg_latency_ms: 1240,
		enabled: true,
	},
	{
		id: "tool_sandbox_python",
		name: "sandbox_python",
		type: "builtin",
		description: "Execute arbitrary Python code in OpenSandbox (CPU=1, mem=2Gi, timeout=10min)",
		provider: "opensandbox",
		input_schema_summary: "{ code: str, packages?: str[], timeout_s?: int = 600 }",
		categories: ["sandbox"],
		last_called_at: "2026-04-07T09:32:10Z",
		call_count_24h: 47,
		avg_latency_ms: 8400,
		enabled: true,
	},
	{
		id: "tool_playwright_scrape",
		name: "playwright_scrape",
		type: "mcp",
		description: "Headless browser scraping via Playwright MCP server",
		provider: "playwright-mcp",
		input_schema_summary: "{ url: str, selector?: str, wait_for?: str }",
		categories: ["market_data", "sandbox"],
		last_called_at: "2026-04-07T07:55:00Z",
		call_count_24h: 12,
		avg_latency_ms: 4200,
		enabled: true,
	},
	{
		id: "tool_exa_search",
		name: "exa_search",
		type: "mcp",
		description: "Semantic web search via Exa API",
		provider: "exa-mcp",
		input_schema_summary: "{ query: str, num_results?: int = 10, type?: 'neural'|'keyword' }",
		categories: ["market_data"],
		last_called_at: "2026-04-07T09:21:00Z",
		call_count_24h: 67,
		avg_latency_ms: 890,
		enabled: true,
	},
	{
		id: "tool_skill_btc_flow",
		name: "btc-onchain-flow",
		type: "skill",
		description: "Personal skill: BTC whale + exchange flow analysis",
		provider: "user-skills",
		input_schema_summary: "{ time_window: str = '24h', min_value_usd?: int = 1000000 }",
		categories: ["market_data"],
		last_called_at: "2026-04-07T07:05:00Z",
		call_count_24h: 8,
		avg_latency_ms: 2100,
		enabled: true,
	},
	{
		id: "tool_delegate_macro",
		name: "delegate_to_macro_analyst",
		type: "a2a",
		description: "Delegate macro analysis sub-task to macro_analyst agent",
		provider: "matrix-a2a",
		input_schema_summary: "{ task: str, deadline_s?: int = 60 }",
		categories: ["a2a"],
		last_called_at: "2026-04-06T16:42:00Z",
		call_count_24h: 4,
		avg_latency_ms: 12300,
		enabled: true,
	},
];

export const mockSemanticCatalog: SemanticCatalogResponse = {
	catalog: {
		version: "1.0.0",
		terms: [
			{
				term_id: "kg_claim",
				name: "KG claim",
				aliases: ["claim", "knowledge claim", "global claim"],
				owner: "matrix",
				status: "active",
				description: "Versioned global knowledge assertion with provenance.",
				source_refs: ["feature-017", "python-backend/memory_engine/global_kg.py"],
				allowed_use: ["agent_answer", "control_ui", "meta_harness"],
				kg_claim_types: ["entity_attribute", "entity_relation"],
				rag_source_classes: ["kg_claim"],
				version: "1.0.0",
				deprecated_by: null,
			},
			{
				term_id: "rag_citation",
				name: "RAG citation",
				aliases: ["citation", "source citation", "evidence citation"],
				owner: "matrix",
				status: "active",
				description: "Document or claim evidence surfaced with an answer.",
				source_refs: ["feature-019", "retrieval/verifiers/citation.py"],
				allowed_use: ["agent_answer", "control_ui", "meta_harness"],
				kg_claim_types: [],
				rag_source_classes: ["document_chunk", "kg_claim"],
				version: "1.0.0",
				deprecated_by: null,
			},
		],
		metrics: [
			{
				metric_id: "agent_tool_success_rate",
				name: "Agent tool success rate",
				measure: "successful_tool_results / total_tool_results",
				dimensions: ["tool_name", "runner_variant", "tenant_id"],
				filters: ["time_range", "tenant_id"],
				grain: "tool_result",
				time_field: "created_at",
				freshness_sla: "15m",
				allowed_aggregations: ["avg"],
				aliases: ["tool success", "tool success rate"],
				owner: "matrix",
				status: "active",
				permission_scope: "tenant",
				source_table: "agent.audit_events",
				source_refs: ["feature-014", "feature-016"],
				version: "1.0.0",
				deprecated_by: null,
			},
			{
				metric_id: "retrieval_pass_rate",
				name: "Retrieval pass rate",
				measure: "passed_canaries / total_canaries",
				dimensions: ["candidate_id", "question_class", "split"],
				filters: ["run_id", "split", "question_class"],
				grain: "canary_result",
				time_field: "generated_at",
				freshness_sla: "run-scoped",
				allowed_aggregations: ["avg"],
				aliases: ["rag pass rate", "retrieval quality"],
				owner: "matrix",
				status: "active",
				permission_scope: "public",
				source_table: "data/meta_harness/runs",
				source_refs: ["feature-022", "feature-023"],
				version: "1.0.0",
				deprecated_by: null,
			},
		],
	},
	validation: {
		passed: true,
		failures: [],
		alias_collisions: {},
	},
};

export const mockReportArtifacts: ReportArtifact[] = [
	{
		report_id: "report-rag-benchmark-summary",
		title: "Matrix RAG Benchmark Summary",
		owner: "matrix",
		status: "validated",
		renderer: "markdown-fallback",
		renderer_version: "builtin",
		generated_at: "2026-04-29T18:20:00Z",
		checksum: "sha256:report-rag-summary-citation",
		manifest_path: "reports/rag-benchmark-summary/manifest.json",
		input_sources: ["artifact-report-rag-benchmark-summary", "feature-022", "feature-019"],
		citations: [
			{
				citation_id: "chunk-report-rag-summary-citation",
				source_id: "artifact-report-rag-benchmark-summary",
				title: "RAG benchmark summary citation",
				uri: "report://matrix/rag-benchmark-summary#citation=chunk-report-rag-summary-citation",
				source_type: "report",
				excerpt:
					"Report manifest citation carries renderer, output path and source artifact metadata.",
			},
		],
		output_files: [
			{
				kind: "manifest",
				path: "reports/rag-benchmark-summary/manifest.json",
				mime_type: "application/json",
			},
			{
				kind: "html",
				path: "reports/rag-benchmark-summary/report.html",
				mime_type: "text/html",
			},
			{
				kind: "source",
				path: "reports/rag-benchmark-summary/source.md",
				mime_type: "text/markdown",
			},
		],
		validation: { passed: true, failures: [] },
		matrix_publication: {
			status: "ready",
			link: "matrix://reports/rag-benchmark-summary",
		},
	},
	{
		report_id: "report-risk-brief-fixture",
		title: "Risk Brief Fixture",
		owner: "risk_manager",
		status: "failed",
		renderer: "quarkdown",
		renderer_version: "experimental",
		generated_at: "2026-04-29T17:10:00Z",
		checksum: "",
		manifest_path: "reports/risk-brief-fixture/manifest.json",
		input_sources: ["feature-027-fixture", "feature-017"],
		citations: [
			{
				citation_id: "S1",
				source_id: "feature-017",
				title: "KG claim provenance fixture",
				source_type: "kg_claim",
			},
		],
		output_files: [
			{
				kind: "manifest",
				path: "reports/risk-brief-fixture/manifest.json",
				mime_type: "application/json",
			},
		],
		validation: {
			passed: false,
			failures: ["citation-not-used:S1", "renderer-fixture-not-promoted"],
		},
		matrix_publication: { status: "blocked" },
	},
];

// ─── Slice 6: Service Status ───────────────────────────────────────────────

export const mockServices: ServiceStatus[] = [
	{
		id: "tuwunel",
		name: "Tuwunel (Matrix Homeserver)",
		tier: "infra",
		port: 8448,
		url: "http://127.0.0.1:8448",
		health: "healthy",
		uptime_s: 14523,
		version: "1.5.2",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "postgres",
		name: "PostgreSQL + pgvector",
		tier: "infra",
		port: 5433,
		health: "healthy",
		uptime_s: 14530,
		version: "16.4",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "nats",
		name: "NATS Message Queue",
		tier: "infra",
		port: 4222,
		health: "healthy",
		uptime_s: 14521,
		version: "2.10.7",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "seaweedfs",
		name: "SeaweedFS S3 (Artifact Storage)",
		tier: "infra",
		port: 8333,
		url: "http://127.0.0.1:8333",
		health: "healthy",
		uptime_s: 14515,
		version: "4.15",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "go-appservice",
		name: "Go Appservice (Matrix Bridge + Storage)",
		tier: "app",
		port: 8090,
		url: "http://127.0.0.1:29318",
		health: "healthy",
		uptime_s: 12340,
		version: "0.4.1",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "agent-service",
		name: "Python Agent Service",
		tier: "app",
		port: 8094,
		url: "http://127.0.0.1:8094",
		health: "healthy",
		uptime_s: 12200,
		version: "0.1.0",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "py-bridge",
		name: "Python Matrix Bridge (NATS Consumer)",
		tier: "app",
		port: 8097,
		health: "healthy",
		uptime_s: 12195,
		version: "0.1.0",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "ingestion-worker",
		name: "Ingestion Worker (Slice 2)",
		tier: "app",
		port: 8098,
		url: "http://127.0.0.1:8098",
		health: "degraded",
		uptime_s: 1240,
		version: "0.1.0",
		last_check: "2026-04-07T09:35:00Z",
		error_message: "DB schema 'ingestion' not yet created — run alembic upgrade head",
	},
	{
		id: "kg-pipeline-worker",
		name: "KG Pipeline Worker (Phase 2 Skeleton)",
		tier: "app",
		port: 8099,
		health: "unknown",
		last_check: "2026-04-07T09:35:00Z",
		error_message: "Phase 2 skeleton — not started",
	},
	{
		id: "extraction-layout-worker",
		name: "Extraction Layout Worker (Phase 2 Skeleton)",
		tier: "app",
		port: 8101,
		health: "unknown",
		last_check: "2026-04-07T09:35:00Z",
		error_message: "Phase 2 skeleton — not started",
	},
	{
		id: "opensandbox",
		name: "OpenSandbox Code Interpreter",
		tier: "app",
		port: 8100,
		url: "http://127.0.0.1:8100",
		health: "healthy",
		uptime_s: 12340,
		version: "1.0.2",
		last_check: "2026-04-07T09:35:00Z",
	},
	{
		id: "control-ui",
		name: "Control UI (Next.js)",
		tier: "app",
		port: 3001,
		url: "http://127.0.0.1:3001",
		health: "healthy",
		uptime_s: 8123,
		version: "16.2",
		last_check: "2026-04-07T09:35:00Z",
	},
];

// ─── ENV Vars (D6 read-only with masking) ──────────────────────────────────

export const mockEnvVars: EnvVar[] = [
	{
		key: "AGENT_PROVIDER",
		value: "anthropic",
		is_sensitive: false,
		source: "env",
		description: "LLM provider for the main agent",
	},
	{
		key: "AGENT_MODEL",
		value: "claude-sonnet-4-6",
		is_sensitive: false,
		source: "env",
	},
	{
		key: "ANTHROPIC_API_KEY",
		value: "sk-ant-api03-••••••••••••••••••••••••••••••f7Yk",
		is_sensitive: true,
		source: "env",
	},
	{
		key: "OPENAI_API_KEY",
		value: "sk-proj-••••••••••••••••••••••••••••••H8mQ",
		is_sensitive: true,
		source: "env",
	},
	{
		key: "HINDSIGHT_DB_URL",
		value: "postgresql://postgres@localhost:5433/hindsight_dev",
		is_sensitive: false,
		source: "env",
	},
	{
		key: "INGESTION_WORKER_URL",
		value: "http://127.0.0.1:8098",
		is_sensitive: false,
		source: "env",
	},
	{
		key: "ARTIFACT_GATEWAY_BASE_URL",
		value: "http://127.0.0.1:29318",
		is_sensitive: false,
		source: "env",
	},
	{
		key: "MATRIX_BOT_ACCESS_TOKEN",
		value: "syt_••••••••••••••••••••••••••••••8k",
		is_sensitive: true,
		source: "env",
	},
	{
		key: "OPEN_SANDBOX_API_KEY",
		value: "E1HuYm••••••••••••••••••••••••••••",
		is_sensitive: true,
		source: "env",
	},
	{
		key: "AGENT_USE_LANGGRAPH",
		value: "true",
		is_sensitive: false,
		source: "env",
	},
	{
		key: "AGENT_TOOL_TIMEOUT_SEC",
		value: "30",
		is_sensitive: false,
		source: "env",
	},
	{
		key: "AGENT_MAX_ITERATIONS",
		value: "10",
		is_sensitive: false,
		source: "env",
	},
];

// ─── Audit Events ──────────────────────────────────────────────────────────

export const mockAuditEvents: AuditEvent[] = [
	{
		id: 1042,
		timestamp: "2026-04-07T09:35:12Z",
		action: "TOOL_CALL",
		user_id: "local",
		thread_id: "thr_a1b2c3",
		agent_class: "advisory",
		agent_role: "fundamentals_analyst",
		tool_name: "get_quote",
		input: { symbol: "NVDA" },
		duration_ms: 47,
		success: true,
	},
	{
		id: 1041,
		timestamp: "2026-04-07T09:34:58Z",
		action: "TOOL_CALL",
		user_id: "local",
		thread_id: "thr_a1b2c3",
		agent_role: "fundamentals_analyst",
		tool_name: "search_news",
		input: { query: "NVDA earnings preview", limit: 10 },
		duration_ms: 312,
		success: true,
	},
	{
		id: 1040,
		timestamp: "2026-04-07T09:34:14Z",
		action: "MEMORY_RETAIN",
		user_id: "local",
		thread_id: "thr_a1b2c3",
		agent_role: "fundamentals_analyst",
		tool_name: "memory_retain",
		input: { content: "NVDA target $1100 — tracking earnings 5/22", fact_type: "personal" },
		duration_ms: 156,
		success: true,
	},
	{
		id: 1039,
		timestamp: "2026-04-07T09:32:10Z",
		action: "SANDBOX_RUN",
		user_id: "local",
		thread_id: "thr_a1b2c3",
		agent_role: "sentiment_analyst",
		tool_name: "sandbox_python",
		duration_ms: 0,
		success: true,
		metadata: { run_id: "sb_002", status: "running" },
	},
	{
		id: 1038,
		timestamp: "2026-04-07T09:21:42Z",
		action: "INGESTION_FAILED",
		user_id: "local",
		duration_ms: 8400,
		success: false,
		error: "DB schema 'ingestion' not yet created — run alembic upgrade head",
		metadata: { file_id: "art_x9y8z7", pipeline: "document" },
	},
	{
		id: 1037,
		timestamp: "2026-04-07T08:42:14Z",
		action: "SANDBOX_FAILED",
		user_id: "local",
		thread_id: "thr_d4e5f6",
		agent_role: "researcher",
		tool_name: "sandbox_python",
		duration_ms: 14000,
		success: false,
		error: "FileNotFoundError: 'positions.csv' not in sandbox",
		metadata: { run_id: "sb_003" },
	},
	{
		id: 1036,
		timestamp: "2026-04-07T08:32:00Z",
		action: "SKILL_USED",
		user_id: "local",
		thread_id: "thr_a1b2c3",
		agent_role: "fundamentals_analyst",
		tool_name: "stock-screener-multifactor",
		duration_ms: 4200,
		success: true,
		metadata: { results_count: 23 },
	},
	{
		id: 1035,
		timestamp: "2026-04-07T08:12:00Z",
		action: "TOOL_CALL",
		user_id: "local",
		thread_id: "thr_d4e5f6",
		agent_role: "risk_manager",
		tool_name: "calc_var",
		duration_ms: 1240,
		success: true,
	},
	{
		id: 1034,
		timestamp: "2026-04-07T07:55:42Z",
		action: "TOOL_CALL",
		user_id: "local",
		thread_id: "thr_a1b2c3",
		agent_role: "fundamentals_analyst",
		tool_name: "playwright_scrape",
		duration_ms: 42100,
		success: true,
	},
	{
		id: 1033,
		timestamp: "2026-04-07T07:05:00Z",
		action: "TOOL_CALL",
		user_id: "local",
		thread_id: "thr_g7h8i9",
		agent_role: "fundamentals_analyst",
		tool_name: "btc-onchain-flow",
		duration_ms: 2100,
		success: true,
	},
	{
		id: 1032,
		timestamp: "2026-04-06T23:21:00Z",
		action: "SANDBOX_TIMEOUT",
		user_id: "local",
		thread_id: "thr_j0k1l2",
		agent_role: "risk_manager",
		tool_name: "sandbox_python",
		duration_ms: 600000,
		success: false,
		error: "Sandbox timeout after 600s",
	},
	{
		id: 1031,
		timestamp: "2026-04-06T18:14:00Z",
		action: "ROLE_OVERRIDE_UPDATED",
		user_id: "local",
		metadata: { role: "researcher", field: "system_prompt", updated_by: "local" },
		success: true,
	},
];

// ─── Sessions (LangGraph Threads) ──────────────────────────────────────────

export const mockSessions: Session[] = [
	{
		thread_id: "thr_a1b2c3",
		user_id: "local",
		role: "fundamentals_analyst",
		created_at: "2026-04-07T07:30:00Z",
		last_message_at: "2026-04-07T09:35:12Z",
		message_count: 47,
		tool_calls: 23,
		is_active: true,
		last_message_preview:
			"NVDA earnings preview shows analysts expecting $26B revenue, +18% YoY...",
	},
	{
		thread_id: "thr_d4e5f6",
		user_id: "local",
		role: "researcher",
		created_at: "2026-04-07T08:00:00Z",
		last_message_at: "2026-04-07T08:42:14Z",
		message_count: 12,
		tool_calls: 7,
		is_active: false,
		last_message_preview:
			"Stress test failed — sandbox missing positions.csv. Will retry after upload.",
	},
	{
		thread_id: "thr_g7h8i9",
		user_id: "local",
		role: "fundamentals_analyst",
		created_at: "2026-04-07T07:00:00Z",
		last_message_at: "2026-04-07T07:05:00Z",
		message_count: 5,
		tool_calls: 2,
		is_active: false,
		last_message_preview: "BTC whale flows: 3 large movements detected, net outflow from exchanges",
	},
	{
		thread_id: "thr_j0k1l2",
		user_id: "local",
		role: "risk_manager",
		created_at: "2026-04-06T23:10:00Z",
		last_message_at: "2026-04-06T23:21:00Z",
		message_count: 3,
		tool_calls: 1,
		is_active: false,
		last_message_preview: "VaR computation timeout after 10 minutes — code likely infinite loop",
	},
	{
		thread_id: "thr_m3n4o5",
		user_id: "local",
		role: "sentiment_analyst",
		created_at: "2026-04-06T15:30:00Z",
		last_message_at: "2026-04-06T16:42:00Z",
		message_count: 28,
		tool_calls: 11,
		is_active: false,
		last_message_preview:
			"Fed pivot signals strengthening — 2y yield down 25bp, dollar weakening...",
	},
];

export const mockOpsReadModel: AgentOpsReadModel = {
	items: mockAuditEvents
		.filter((event) => event.tool_name)
		.map((event) => {
			const tool = mockTools.find((item) => item.name === event.tool_name);
			return {
				id: `audit:${event.id}`,
				source: "audit",
				event_type:
					event.action.toLowerCase().includes("memory") || event.tool_name?.includes("memory")
						? "memory"
						: "tool_call",
				status: event.success ? "active" : "blocked",
				timestamp: event.timestamp,
				thread_id: event.thread_id,
				user_id: event.user_id,
				agent_role: event.agent_role,
				tool_name: event.tool_name,
				action: event.action,
				success: event.success,
				risk: tool?.risk ?? "unrated",
				audit_ref: String(event.id),
				duration_ms: event.duration_ms,
				error: event.error,
				input: event.input,
				output: event.output,
				metadata: event.metadata,
				linked_surfaces:
					event.id === 1042
						? {
								prompt_cache: {
									surface: "prompt_cache",
									label: "Prompt Cache",
									href: "/control/prompt-cache?thread_id=thr_a1b2c3",
									provider: "openrouter",
									model: "provider/mock-model",
									prompt_digest: "mock-prompt-digest",
									tool_catalog_digest: "mock-tool-digest",
									cache_read_tokens: 5120,
									cache_write_tokens: 256,
									cache_break_reasons: [],
								},
								report_artifacts: [
									{
										surface: "report_artifact",
										label: "Report report-rag-benchmark-summary",
										href: "/control/reports?report_id=report-rag-benchmark-summary",
										report_id: "report-rag-benchmark-summary",
										manifest_path: "reports/report-rag-benchmark-summary/manifest.json",
										output_path: "reports/report-rag-benchmark-summary/report.html",
										status: "validated",
									},
								],
							}
						: undefined,
				runtime_events:
					event.action.toLowerCase().includes("memory") || event.tool_name?.includes("memory")
						? [
								{
									contract: "agent-runtime-event/v1",
									kind: "memory",
									status: event.success ? "completed" : "failed",
									name: event.success ? "memory.recall.completed" : "memory.recall.failed",
									summary: "Memory runtime event from audit mock",
									timestamp: event.timestamp,
									audit_ref: String(event.id),
								},
							]
						: [
								{
									contract: "agent-runtime-event/v1",
									kind: "tool",
									status: event.success ? "completed" : "failed",
									name: event.tool_name ?? event.action,
									summary: "Tool runtime event from audit mock",
									timestamp: event.timestamp,
									audit_ref: String(event.id),
								},
							],
				runtime_event_count: 1,
			};
		}),
	subagent_runs: [
		{
			run_id: "task-researcher-child",
			child_task_id: "task-researcher-child",
			parent_thread_id: "thr_a1b2c3",
			role: "researcher",
			delegate_kind: "leaf",
			status: "completed",
			started_at: "2026-04-29T11:56:10Z",
			ended_at: "2026-04-29T11:58:34Z",
			event_count: 2,
			spawn_depth: 0,
			next_spawn_depth: 1,
			max_spawn_depth: 1,
			controls: {
				status: "supported",
				kill: "unsupported",
				pause: "unsupported",
				replay: "unsupported",
			},
			last_event: {
				contract: "agent-runtime-event/v1",
				kind: "subagent",
				status: "completed",
				name: "subagent.completed",
				summary: "Research delegation completed",
				thread_id: "thr_a1b2c3",
				timestamp: "2026-04-29T11:58:34Z",
				metadata: {
					child_task_id: "task-researcher-child",
					role: "researcher",
					delegate_kind: "leaf",
				},
			},
		},
	],
	sessions: mockSessions.map((session) => {
		const events = mockAuditEvents.filter((event) => event.thread_id === session.thread_id);
		return {
			thread_id: session.thread_id,
			status: events.some((event) => !event.success)
				? "blocked"
				: session.is_active
					? "active"
					: "replay",
			agent_role: session.role,
			checkpoint_count: session.checkpoint_count ?? session.message_count ?? 0,
			event_count: events.length,
			tool_count: events.filter((event) => event.tool_name).length,
			last_checkpoint: session.last_checkpoint ?? session.last_message_at,
		};
	}),
	blockers: [],
	approvals: [],
	runtime_events: [],
	runtime_summary: {
		total: 0,
		by_kind: {},
		by_status: {},
		latest: {},
	},
	filters: {},
	summary: {
		total_events: mockAuditEvents.filter((event) => event.tool_name).length,
		sessions: mockSessions.length,
		tool_events: mockAuditEvents.filter((event) => event.tool_name).length,
		blockers: mockAuditEvents.filter((event) => !event.success).length,
		approvals: 0,
		runtime_events: 0,
		subagent_runs: 1,
		generated_at: "2026-04-29T12:00:00Z",
	},
	limit: 100,
	offset: 0,
	contract: "agent-ops-event/v1",
};
mockOpsReadModel.blockers = mockOpsReadModel.items.filter((event) => event.status === "blocked");
mockOpsReadModel.runtime_events = mockOpsReadModel.items.flatMap(
	(event) => event.runtime_events ?? [],
);
mockOpsReadModel.runtime_summary = {
	total: mockOpsReadModel.runtime_events.length,
	by_kind: mockOpsReadModel.runtime_events.reduce<Record<string, number>>((acc, event) => {
		const key = String(event.kind ?? "unknown");
		acc[key] = (acc[key] ?? 0) + 1;
		return acc;
	}, {}),
	by_status: mockOpsReadModel.runtime_events.reduce<Record<string, number>>((acc, event) => {
		const key = String(event.status ?? "unknown");
		acc[key] = (acc[key] ?? 0) + 1;
		return acc;
	}, {}),
	latest: mockOpsReadModel.runtime_events[0] ?? {},
};
mockOpsReadModel.summary.runtime_events = mockOpsReadModel.runtime_events.length;

export const mockPromptCacheReadModel: PromptCacheReadModel = {
	contract: "prompt-cache-read-model/v1",
	items: [
		{
			event_id: "audit:1042",
			audit_ref: "1042",
			timestamp: "2026-04-07T09:35:12Z",
			thread_id: "thr_a1b2c3",
			provider: "openrouter",
			model: "provider/mock-model",
			router: "langgraph",
			iteration: 3,
			prompt_digest: "mock-prompt-digest",
			prompt_layout_digest: "mock-layout-digest",
			tool_catalog_digest: "mock-tool-digest",
			cache_break_reasons: [],
			usage: {
				prompt_tokens: 8192,
				completion_tokens: 768,
				total_tokens: 8960,
				cache_read_tokens: 5120,
				cache_write_tokens: 256,
				unknown_fields: [],
			},
			links: {
				ops_event: "/control/ops?session=thr_a1b2c3",
				context: "/control/context?thread_id=thr_a1b2c3",
			},
		},
		{
			event_id: "audit:1035",
			audit_ref: "1035",
			timestamp: "2026-04-07T08:12:00Z",
			thread_id: "thr_d4e5f6",
			provider: "openrouter",
			model: "provider/mock-model",
			router: "simple",
			iteration: 1,
			prompt_digest: "mock-prompt-digest-2",
			prompt_layout_digest: "mock-layout-digest-2",
			tool_catalog_digest: "mock-tool-digest-2",
			cache_break_reasons: ["tool_catalog_changed"],
			usage: {
				prompt_tokens: 4096,
				completion_tokens: 512,
				total_tokens: 4608,
				cache_read_tokens: 0,
				cache_write_tokens: 128,
				unknown_fields: ["reasoning_tokens"],
			},
			links: {
				ops_event: "/control/ops?session=thr_d4e5f6",
				context: "/control/context?thread_id=thr_d4e5f6",
			},
		},
	],
	summary: {
		requests: 2,
		cache_read_tokens: 5120,
		cache_write_tokens: 384,
		prompt_tokens: 12288,
		completion_tokens: 1280,
		total_tokens: 13568,
		cache_breaks: 1,
		unknown_cache_fields: 0,
		generated_at: "2026-04-30T10:00:00Z",
	},
	by_provider: { openrouter: 2 },
	by_model: { "provider/mock-model": 2 },
	cache_break_reasons: { tool_catalog_changed: 1 },
	limit: 100,
};

export const mockWidgetProposals: MatrixWidgetApprovalItem[] = [
	{
		proposal_id: "report-widget-risk-brief",
		report_id: "risk-brief",
		title: "Risk Brief",
		room_id: "!risk:example.test",
		requester_user_id: "@agent:example.test",
		url: "https://widgets.example/reports/risk-brief",
		resource_uri: "report://matrix/risk-brief",
		status: "pending",
		approval_required: true,
		can_approve: true,
		can_deny: true,
		denial_reasons: [],
		fallback_markdown: "[Risk Brief](https://widgets.example/reports/risk-brief) - report artifact",
		permissions: ["read_room"],
		audit_refs: ["audit-report-build"],
		report_artifact: {
			manifest_id: "risk-brief/manifest.json",
			output_path: "risk-brief/report.html",
			renderer: "markdown-fallback",
		},
		matrix_publication: {
			room_id: "!risk:example.test",
			status: "ready",
		},
		validation: {
			passed: true,
			failures: [],
		},
	},
	{
		proposal_id: "report-widget-blocked-origin",
		report_id: "blocked-origin",
		title: "Blocked Origin",
		room_id: "!risk:example.test",
		requester_user_id: "@agent:example.test",
		url: "https://blocked.example/reports/blocked-origin",
		resource_uri: "report://matrix/blocked-origin",
		status: "blocked",
		approval_required: false,
		can_approve: false,
		can_deny: false,
		denial_reasons: ["widget-origin-not-allowed"],
		fallback_markdown: "Blocked Origin (blocked widget URL)",
		permissions: ["read_room"],
		audit_refs: ["audit-report-build"],
		report_artifact: {
			manifest_id: "blocked-origin/manifest.json",
			output_path: "blocked-origin/report.html",
			renderer: "markdown-fallback",
		},
		matrix_publication: {
			status: "blocked",
		},
		validation: {
			passed: true,
			failures: [],
		},
	},
];

// ─── MCP Servers ───────────────────────────────────────────────────────────

export const mockMcpServers: McpServer[] = [
	{
		id: "mcp_playwright",
		name: "Playwright MCP",
		url: "stdio://npx @modelcontextprotocol/server-playwright",
		transport: "stdio",
		status: "connected",
		tools: ["playwright_scrape", "playwright_screenshot", "playwright_pdf"],
		last_ping: "2026-04-07T09:34:00Z",
	},
	{
		id: "mcp_exa",
		name: "Exa Search MCP",
		url: "stdio://npx exa-mcp",
		transport: "stdio",
		status: "connected",
		tools: ["exa_search", "exa_find_similar"],
		last_ping: "2026-04-07T09:34:00Z",
	},
	{
		id: "mcp_filesystem",
		name: "Filesystem MCP",
		url: "stdio://npx @modelcontextprotocol/server-filesystem /workspace",
		transport: "stdio",
		status: "connected",
		tools: ["read_file", "write_file", "list_directory"],
		last_ping: "2026-04-07T09:34:00Z",
	},
	{
		id: "mcp_github",
		name: "GitHub MCP",
		url: "https://api.github.com/mcp",
		transport: "http",
		status: "disconnected",
		tools: ["github_search", "github_create_pr", "github_list_issues"],
		error: "API token expired",
	},
	{
		id: "mcp_matrix",
		name: "Matrix Internal MCP",
		url: "http://127.0.0.1:8094/mcp",
		transport: "http",
		status: "connected",
		tools: ["memory_retain", "memory_recall", "kg_query", "search_news", "get_quote"],
		last_ping: "2026-04-07T09:34:30Z",
	},
];

// ─── A2A Delegations ───────────────────────────────────────────────────────

export const mockA2A: A2ADelegation[] = [
	{
		id: "a2a_001",
		from_role: "fundamentals_analyst",
		to_role: "sentiment_analyst",
		task: "What is the current Fed funds rate trajectory expectation for Q2-Q3 2026?",
		status: "completed",
		started_at: "2026-04-07T09:21:00Z",
		completed_at: "2026-04-07T09:21:42Z",
		result_preview:
			"Market pricing 2 cuts by Q3 (50bp total). Recent CPI miss strengthened pivot odds — Powell speech next Tuesday key.",
		thread_id: "thr_a1b2c3",
	},
	{
		id: "a2a_002",
		from_role: "researcher",
		to_role: "risk_manager",
		task: "Approve adding 3% NVDA position before earnings",
		status: "failed",
		started_at: "2026-04-07T08:42:00Z",
		completed_at: "2026-04-07T08:42:14Z",
		result_preview:
			"REJECTED: Pre-earnings exposure already at 8% (threshold 5%). Reduce other tech first.",
		thread_id: "thr_d4e5f6",
	},
	{
		id: "a2a_003",
		from_role: "sentiment_analyst",
		to_role: "technical_analyst",
		task: "Flag any client trades in semiconductor names this week",
		status: "running",
		started_at: "2026-04-07T09:30:00Z",
		thread_id: "thr_m3n4o5",
	},
	{
		id: "a2a_004",
		from_role: "researcher",
		to_role: "trader",
		task: "Execute TWAP buy: AAPL 10000 shares over next 2 hours",
		status: "pending",
		started_at: "2026-04-07T09:34:00Z",
		thread_id: "thr_d4e5f6",
	},
];

// ─── Slice 7: Overview Snapshot (TT1) ─────────────────────────────────────

export const mockOverview: OverviewSnapshot = {
	ai_health: "online",
	ai_health_message: "All 11 services healthy · ingestion worker degraded (alembic pending)",
	active_sessions: 2,
	active_tasks: 1,
	memory_facts_total: 1423,
	kg_nodes_total: 217,
	last_agent_error: {
		timestamp: "2026-04-07T08:42:14Z",
		role: "researcher",
		message: "FileNotFoundError: 'positions.csv' not in sandbox",
	},
	recent_activity: [
		{
			timestamp: "2026-04-07T09:35:12Z",
			text: "fundamentals_analyst · get_quote(NVDA) · 47ms",
			kind: "tool_call",
		},
		{
			timestamp: "2026-04-07T09:34:58Z",
			text: "fundamentals_analyst · search_news(NVDA earnings)",
			kind: "tool_call",
		},
		{
			timestamp: "2026-04-07T09:34:14Z",
			text: "Memory retain: 'NVDA target $1100'",
			kind: "memory",
		},
		{
			timestamp: "2026-04-07T09:32:10Z",
			text: "sentiment_analyst · sandbox_python (running)",
			kind: "sandbox",
		},
		{
			timestamp: "2026-04-07T09:21:42Z",
			text: "Ingestion failed: alembic pending",
			kind: "error",
		},
	],
};

export const mockContextInspector: ContextInspectorResponse = {
	stats: {
		memoryProvider: "memory_fusion",
		kgNodeCount: 217,
		kgEdgeCount: 19,
		kgHealth: "healthy",
		hasPersistedRunMetadata: true,
		liveContextBlockCount: 4,
	},
	activeSession: {
		sessionId: "sess_ctx_001",
		threadId: "thread_ctx_001",
		status: "completed",
		provider: "openrouter",
		model: "openrouter/anthropic/claude-sonnet",
		promptTokens: 8234,
		completionTokens: 742,
		cachedTokens: 5120,
		totalTokens: 8976,
		updatedAt: "2026-04-16T18:45:00Z",
	},
	sourceLayerCounts: {
		personal_raw: 2,
		personal_derived: 1,
		bridge_world: 1,
	},
	contextBlocks: [
		{
			id: "ctx_raw_1",
			title: "Chat Turn",
			preview: "User asked to compare macro catalysts with the latest BTC regime shift.",
			sourceLayer: "personal_raw",
			sourceType: "user_input",
			artifactType: "chat_turn",
			groundingStatus: "not_applicable",
			provenanceRef: "session-001.jsonl#0",
			status: "available",
			tokenCount: 19,
		},
		{
			id: "ctx_pref_1",
			title: "Preference",
			preview: "Prefer concise summaries first, then supporting evidence.",
			sourceLayer: "personal_derived",
			sourceType: "system_observation",
			artifactType: "preference",
			groundingStatus: "grounded_derived",
			provenanceRef: "session-001.jsonl#3",
			status: "available",
			tokenCount: 11,
		},
		{
			id: "ctx_world_1",
			title: "World Evidence",
			preview: "FOMC minutes shifted rate-cut expectations for the next quarter.",
			sourceLayer: "bridge_world",
			sourceType: "world_evidence",
			artifactType: "world_evidence",
			groundingStatus: "not_applicable",
			provenanceRef: "macro-feed#2026-04-16-1",
			status: "available",
			tokenCount: 13,
		},
	],
	degradationFlags: ["NO_PERSONAL_KB"],
	worldClaims: [
		{
			id: "ctx_world_1",
			title: "World Evidence",
			preview: "FOMC minutes shifted rate-cut expectations for the next quarter.",
			sourceLayer: "bridge_world",
			sourceType: "world_evidence",
			artifactType: "world_evidence",
			groundingStatus: "not_applicable",
			provenanceRef: "macro-feed#2026-04-16-1",
			status: "available",
			tokenCount: 13,
		},
	],
	userId: "local",
	bankId: "user_local",
};

// ─── Slice 7: Security Posture (TT8) ──────────────────────────────────────

export const mockSecurity: SecurityPosture = {
	overall_score: 82,
	pillars: [
		{
			name: "Authentication",
			score: 95,
			status: "good",
			message: "API keys set for Anthropic + OpenAI. Session auth via matrix_bot_token.",
		},
		{
			name: "Encryption",
			score: 70,
			status: "warning",
			message: "Matrix E2EE disabled in dev (MATRIX_E2EE_ENABLED=false). TLS not enforced locally.",
		},
		{
			name: "Audit",
			score: 100,
			status: "good",
			message: "1042 events in last 24h covering all mutating actions.",
		},
		{
			name: "Network",
			score: 60,
			status: "warning",
			message:
				"All services on 127.0.0.1 loopback only — good for dev. No firewall rules set for prod yet.",
		},
	],
	recent_events: [
		{
			timestamp: "2026-04-06T18:14:00Z",
			type: "role_change",
			actor: "local",
			description: "researcher system_prompt overridden",
			severity: "info",
		},
		{
			timestamp: "2026-04-07T08:32:00Z",
			type: "sensitive_tool_call",
			actor: "fundamentals_analyst",
			description: "stock-screener-multifactor returned 23 results",
			severity: "info",
		},
		{
			timestamp: "2026-04-07T09:21:42Z",
			type: "permission_change",
			actor: "system",
			description: "consent_overrides reloaded",
			severity: "info",
		},
	],
	access_list: [
		{
			session_id: "sess_local_dev",
			ip: "127.0.0.1",
			user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128",
			first_seen: "2026-04-07T06:30:00Z",
			last_seen: "2026-04-07T09:35:12Z",
		},
	],
};

// ─── Slice 7: LLM Providers (ApiModelsTab) ────────────────────────────────

export const mockLlmProviders: LlmProvider[] = [
	{
		id: "anthropic",
		display_name: "Anthropic",
		type: "cloud",
		api_key_set: true,
		api_key_preview: "sk-ant-••••f7Yk",
		is_active: true,
		available_models: ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
	},
	{
		id: "openai",
		display_name: "OpenAI",
		type: "cloud",
		api_key_set: true,
		api_key_preview: "sk-proj-••••H8mQ",
		is_active: true,
		available_models: ["gpt-4o", "gpt-4o-mini", "o3-mini"],
	},
	{
		id: "gemini",
		display_name: "Google Gemini",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "mistral",
		display_name: "Mistral",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "groq",
		display_name: "Groq",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "cohere",
		display_name: "Cohere",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "openrouter",
		display_name: "OpenRouter",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "deepseek",
		display_name: "DeepSeek",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "qwen",
		display_name: "Qwen (DashScope)",
		type: "cloud",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "ollama",
		display_name: "Ollama",
		type: "local",
		api_key_set: false,
		endpoint_url: "http://localhost:11434",
		is_active: false,
		available_models: [],
	},
	{
		id: "vllm",
		display_name: "vLLM",
		type: "local",
		api_key_set: false,
		is_active: false,
		available_models: [],
	},
	{
		id: "lmstudio",
		display_name: "LM Studio",
		type: "local",
		api_key_set: false,
		endpoint_url: "http://localhost:1234/v1",
		is_active: false,
		available_models: [],
	},
];

// ─── Slice 7: Model Routing (per role) ────────────────────────────────────

export const mockModelRouting: ModelRouting[] = [
	{
		role_id: "fundamentals_analyst",
		provider_id: "anthropic",
		model_id: "claude-sonnet-4-6",
		is_default: true,
	},
	{
		role_id: "researcher",
		provider_id: "anthropic",
		model_id: "claude-opus-4-6",
		is_default: false,
	},
	{
		role_id: "risk_manager",
		provider_id: "anthropic",
		model_id: "claude-sonnet-4-6",
		is_default: true,
	},
	{
		role_id: "sentiment_analyst",
		provider_id: "openai",
		model_id: "gpt-4o",
		is_default: false,
	},
	{
		role_id: "trader",
		provider_id: "anthropic",
		model_id: "claude-haiku-4-5-20251001",
		is_default: false,
	},
	{
		role_id: "technical_analyst",
		provider_id: "anthropic",
		model_id: "claude-sonnet-4-6",
		is_default: true,
	},
];

// ─── Slice 7: Utility Models ──────────────────────────────────────────────

export const mockUtilityModels: UtilityModel[] = [
	{
		purpose: "embedder_text",
		display_name: "Text Embedder",
		provider_id: "local-st",
		model_id: "sentence-transformers/all-MiniLM-L6-v2",
		is_local: true,
		is_active: true,
		notes: "384 dim, ~80MB, CPU",
	},
	{
		purpose: "embedder_visual",
		display_name: "Visual Embedder (ColPali)",
		provider_id: "phase2",
		model_id: "vidore/colpali-v1.3",
		is_local: true,
		is_active: false,
		notes: "Phase 2 — lives in extraction_layout venv",
	},
	{
		purpose: "reranker",
		display_name: "Cross-Encoder Reranker",
		provider_id: "local-bge",
		model_id: "BAAI/bge-reranker-v2-m3",
		is_local: true,
		is_active: false,
		notes: "Phase 3 retrieval",
	},
	{
		purpose: "summarizer",
		display_name: "Summarizer",
		provider_id: "anthropic",
		model_id: "claude-haiku-4-5-20251001",
		is_local: false,
		is_active: true,
	},
	{
		purpose: "stt",
		display_name: "Speech-to-Text",
		provider_id: "local-whisper",
		model_id: "whisper-base",
		is_local: true,
		is_active: true,
		notes: "faster-whisper, CPU",
	},
	{
		purpose: "tts",
		display_name: "Text-to-Speech",
		provider_id: "local-piper",
		model_id: "piper-en_US-libritts_r-medium",
		is_local: true,
		is_active: true,
	},
];
