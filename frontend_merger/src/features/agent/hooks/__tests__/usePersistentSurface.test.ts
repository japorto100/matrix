import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePersistentSurface } from "../usePersistentSurface";

const SCHEMA_VERSION = 1;

const fetchMock = vi.fn();

beforeEach(() => {
	window.localStorage.clear();
	fetchMock.mockReset();
	// Default: server reports "no record" — keeps localStorage-only behaviour
	// identical to Phase-1 for tests that don't care about server sync.
	fetchMock.mockResolvedValue(
		new Response(JSON.stringify({ error: "surface not found" }), {
			status: 404,
			headers: { "content-type": "application/json" },
		}),
	);
	globalThis.fetch = fetchMock as unknown as typeof fetch;
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("usePersistentSurface (Phase-2, BFF-synced)", () => {
	it("loads nothing on first mount when storage + server empty", async () => {
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toBeNull();
		await waitFor(() => expect(fetchMock).toHaveBeenCalled());
		expect(result.current.surfaceJson).toBeNull();
	});

	it("persists save to localStorage with schema_version and PUTs to server", async () => {
		const { result } = renderHook(() => usePersistentSurface("main"));
		act(() => {
			result.current.save({ type: "Card", children: [] });
		});
		const stored = window.localStorage.getItem("a2ui.surface.main");
		expect(stored).toBeTruthy();
		const parsed = JSON.parse(stored!);
		expect(parsed.schema_version).toBe(SCHEMA_VERSION);
		expect(parsed.surface_json).toEqual({ type: "Card", children: [] });
		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalledWith(
				"/api/surfaces/main",
				expect.objectContaining({ method: "PUT" }),
			);
		});
	});

	it("renders cache immediately on mount (before server hydrate)", () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({ schema_version: SCHEMA_VERSION, surface_json: { type: "Card" } }),
		);
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toEqual({ type: "Card" });
	});

	it("reconciles with server record when it arrives after cache", async () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({ schema_version: SCHEMA_VERSION, surface_json: { type: "Card" } }),
		);
		fetchMock.mockResolvedValueOnce(
			new Response(
				JSON.stringify({
					schema_version: SCHEMA_VERSION,
					surface_json: { type: "Grid" },
					updated_at: "2026-04-24T10:00:00Z",
				}),
				{ status: 200, headers: { "content-type": "application/json" } },
			),
		);
		const { result } = renderHook(() => usePersistentSurface("main"));
		// Immediate cache hit
		expect(result.current.surfaceJson).toEqual({ type: "Card" });
		// Server overrides after hydrate
		await waitFor(() => expect(result.current.surfaceJson).toEqual({ type: "Grid" }));
	});

	it("drops stale schema_version on mount", () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({ schema_version: 99, surface_json: { type: "Card" } }),
		);
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toBeNull();
		expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
	});

	it("clear() removes storage + state and DELETEs on server", async () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({ schema_version: SCHEMA_VERSION, surface_json: { type: "Card" } }),
		);
		fetchMock.mockResolvedValueOnce(new Response(null, { status: 404 })); // initial GET (server has no record yet)
		fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 })); // DELETE
		const { result } = renderHook(() => usePersistentSurface("main"));
		act(() => {
			result.current.clear();
		});
		expect(result.current.surfaceJson).toBeNull();
		expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalledWith(
				"/api/surfaces/main",
				expect.objectContaining({ method: "DELETE" }),
			);
		});
	});

	it("recovers from corrupted JSON by clearing the entry", () => {
		window.localStorage.setItem("a2ui.surface.main", "not-json{{{");
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toBeNull();
		expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
	});

	it("surfaces syncState=error when server load fails", async () => {
		fetchMock.mockReset();
		fetchMock.mockResolvedValue(new Response(null, { status: 500 }));
		const { result } = renderHook(() => usePersistentSurface("main"));
		await waitFor(() => expect(result.current.syncState).toBe("error"));
	});
});
