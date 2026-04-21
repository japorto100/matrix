/**
 * CopilotKit Runtime Endpoint.
 *
 * Thin BFF proxy: OpenAIAdapter with baseURL → LiteLLM → provider-agnostic.
 * All LLM calls go through localhost:4000 (LiteLLM gateway) which routes to
 * OpenRouter / Anthropic / OpenAI / Ollama per user config.
 *
 * Spec: docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md §17.1.10
 */

import {
	CopilotRuntime,
	copilotRuntimeNextJSAppRouterEndpoint,
	OpenAIAdapter,
} from "@copilotkit/runtime";
import type { NextRequest } from "next/server";
import OpenAI from "openai";

const LITELLM_BASE_URL =
	process.env.LITELLM_BASE_URL ??
	process.env.NEXT_PUBLIC_LITELLM_BASE_URL ??
	"http://localhost:4000";

const DEFAULT_MODEL = process.env.COPILOTKIT_DEFAULT_MODEL ?? "anthropic/claude-haiku-4-5";

const openai = new OpenAI({
	baseURL: LITELLM_BASE_URL,
	apiKey: process.env.LITELLM_API_KEY ?? "sk-not-used-with-litellm",
});

const serviceAdapter = new OpenAIAdapter({ openai, model: DEFAULT_MODEL });
const runtime = new CopilotRuntime();

export const POST = async (req: NextRequest) => {
	const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
		runtime,
		serviceAdapter,
		endpoint: "/api/copilotkit",
	});
	return handleRequest(req);
};

export const OPTIONS = async () =>
	new Response(null, {
		status: 204,
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Methods": "POST, OPTIONS",
			"Access-Control-Allow-Headers": "content-type, authorization",
		},
	});
