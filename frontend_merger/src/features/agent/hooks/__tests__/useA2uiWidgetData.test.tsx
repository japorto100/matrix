import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useA2uiWidgetData } from "../useA2uiWidgetData";

const fetchMock = vi.fn();

function wrapper(children: ReactNode) {
	const qc = new QueryClient({
		defaultOptions: { queries: { retry: false, gcTime: 0 } },
	});
	return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
	fetchMock.mockReset();
	globalThis.fetch = fetchMock as unknown as typeof fetch;
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("useA2uiWidgetData", () => {
	it("fetches /api/a2ui/<dataRef> with no params", async () => {
		fetchMock.mockResolvedValueOnce(
			new Response(JSON.stringify({ price: 42 }), {
				status: 200,
				headers: { "content-type": "application/json" },
			}),
		);
		const { result } = renderHook(() => useA2uiWidgetData<{ price: number }>("tickers/AAPL"), {
			wrapper: ({ children }) => wrapper(children),
		});
		await waitFor(() => expect(result.current.isSuccess).toBe(true));
		expect(result.current.data).toEqual({ price: 42 });
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/a2ui/tickers/AAPL",
			expect.objectContaining({ method: "GET" }),
		);
	});

	it("appends query-string params when provided", async () => {
		fetchMock.mockResolvedValueOnce(
			new Response(JSON.stringify([]), {
				status: 200,
				headers: { "content-type": "application/json" },
			}),
		);
		renderHook(() => useA2uiWidgetData("search", { q: "foo", limit: 10 }), {
			wrapper: ({ children }) => wrapper(children),
		});
		await waitFor(() => expect(fetchMock).toHaveBeenCalled());
		expect(fetchMock.mock.calls[0][0]).toBe("/api/a2ui/search?q=foo&limit=10");
	});

	it("surfaces ApiError on non-2xx", async () => {
		fetchMock.mockResolvedValueOnce(
			new Response(JSON.stringify({ error: "not found" }), {
				status: 404,
				headers: { "content-type": "application/json" },
			}),
		);
		const { result } = renderHook(() => useA2uiWidgetData("missing"), {
			wrapper: ({ children }) => wrapper(children),
		});
		await waitFor(() => expect(result.current.isError).toBe(true));
		expect(result.current.error).toBeTruthy();
	});
});
