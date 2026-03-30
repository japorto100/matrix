/**
 * AI SDK v6 DevTools — Middleware für LLM Call Debugging.
 *
 * Aktivierung:
 *   1. `npx @ai-sdk/devtools` startet den DevTools Viewer auf http://localhost:4983
 *   2. Diese Middleware wrapped das Model und loggt alle Calls automatisch
 *
 * Nur für Development — nie in Production verwenden (speichert Prompts/Responses lokal).
 *
 * Zusätzlich: Next.js 16.2 hat built-in Agent DevTools Panel (zero-config mit AI SDK v6)
 *   → Sichtbar im Browser Dev Panel wenn Next.js im Dev-Modus läuft
 */

import { wrapLanguageModel, type LanguageModel } from "ai";

let devToolsMiddleware: ((options?: Record<string, unknown>) => unknown) | null = null;

// Lazy import — devtools package nur in development laden
async function getDevToolsMiddleware() {
	if (devToolsMiddleware) return devToolsMiddleware;
	if (process.env.NODE_ENV !== "development") return null;
	try {
		const mod = await import("@ai-sdk/devtools");
		devToolsMiddleware = mod.devToolsMiddleware;
		return devToolsMiddleware;
	} catch {
		return null;
	}
}

/**
 * Wrapped ein Language Model mit DevTools Middleware (nur in Development).
 * In Production gibt es das Original-Model unverändert zurück.
 */
export async function withDevTools(model: LanguageModel): Promise<LanguageModel> {
	const middleware = await getDevToolsMiddleware();
	if (!middleware) return model;
	return wrapLanguageModel({
		model,
		middleware: middleware() as Parameters<typeof wrapLanguageModel>[0]["middleware"],
	});
}
