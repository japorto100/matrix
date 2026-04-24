"use client";

import { useQuery, type UseQueryOptions, type UseQueryResult } from "@tanstack/react-query";
import { apiGet } from "@/lib/queries/client";

/**
 * Plan-v2 Phase-2 #34 — on-demand data-binding for A2UI widgets.
 *
 * Lives inside widget components to fetch/cache/refresh data that is
 * NOT pushed by the agent (Ansatz-X `data-a2ui-update-data-model`
 * packets handle push). Used for:
 *   - User-initiated refresh (a "reload" button in the widget)
 *   - Paginated lists (page N loaded on demand)
 *   - Filter changes (re-fetch with new params)
 *   - Deep details on click (lazy-load a row's full payload)
 *
 * Endpoint contract: the agent is expected to expose a REST route at
 * `/api/a2ui/<dataRef>` via the BFF. dataRef is an opaque identifier
 * the agent embedded in the widget spec ("tickers", "positions/AAPL",
 * etc.). The BFF proxies to the Go gateway / Python agent as needed.
 *
 * Three composition patterns widgets use:
 *
 *   // 1. Simple fetch bound to the widget's dataRef
 *   const { data } = useA2uiWidgetData<Ticker>("tickers/AAPL");
 *
 *   // 2. Parameterised (search box, filter bar)
 *   const { data } = useA2uiWidgetData<Result[]>("search", { q: "foo" });
 *
 *   // 3. Opt-in freshness (polling ticker that agent isn't streaming)
 *   const { data } = useA2uiWidgetData<Price>("price/AAPL", undefined, {
 *       refetchInterval: 5000,
 *   });
 */

export interface UseA2uiWidgetDataOptions<TData>
	extends Omit<UseQueryOptions<TData, Error, TData>, "queryKey" | "queryFn"> {}

function buildUrl(dataRef: string, params?: Record<string, string | number | boolean>): string {
	const base = `/api/a2ui/${encodeURI(dataRef.replace(/^\/+/, ""))}`;
	if (!params || Object.keys(params).length === 0) return base;
	const qs = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) qs.set(k, String(v));
	return `${base}?${qs.toString()}`;
}

export function useA2uiWidgetData<TData = unknown>(
	dataRef: string,
	params?: Record<string, string | number | boolean>,
	options?: UseA2uiWidgetDataOptions<TData>,
): UseQueryResult<TData, Error> {
	const url = buildUrl(dataRef, params);
	return useQuery<TData, Error, TData>({
		queryKey: ["a2ui-widget-data", dataRef, params ?? null],
		queryFn: () => apiGet<TData>(url),
		// Agent-pushed data updates (via SSE) do not invalidate this cache
		// automatically — widgets that want live-sync should use the
		// pushed data model + subscribe via useA2UIStore. This hook is
		// the pull-side for data the agent does not stream.
		staleTime: 30_000,
		...options,
	});
}
