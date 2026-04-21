import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePersistentSurface } from "../usePersistentSurface";

const SCHEMA_VERSION = 1;

beforeEach(() => {
	window.localStorage.clear();
});

describe("usePersistentSurface (localStorage-only)", () => {
	it("loads nothing on first mount when storage empty", () => {
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toBeNull();
	});

	it("persists save to localStorage with schema_version", () => {
		const { result } = renderHook(() => usePersistentSurface("main"));
		act(() => {
			result.current.save({ type: "Card", children: [] });
		});
		const stored = window.localStorage.getItem("a2ui.surface.main");
		expect(stored).toBeTruthy();
		const parsed = JSON.parse(stored!);
		expect(parsed.schema_version).toBe(SCHEMA_VERSION);
		expect(parsed.surface_json).toEqual({ type: "Card", children: [] });
	});

	it("loads existing valid surface on mount", () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({
				schema_version: SCHEMA_VERSION,
				surface_json: { type: "Card" },
			}),
		);
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toEqual({ type: "Card" });
	});

	it("drops stale schema_version on mount", () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({
				schema_version: 99,
				surface_json: { type: "Card" },
			}),
		);
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toBeNull();
		expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
	});

	it("clear() removes storage + state", () => {
		window.localStorage.setItem(
			"a2ui.surface.main",
			JSON.stringify({
				schema_version: SCHEMA_VERSION,
				surface_json: { type: "Card" },
			}),
		);
		const { result } = renderHook(() => usePersistentSurface("main"));
		act(() => {
			result.current.clear();
		});
		expect(result.current.surfaceJson).toBeNull();
		expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
	});

	it("recovers from corrupted JSON by clearing the entry", () => {
		window.localStorage.setItem("a2ui.surface.main", "not-json{{{");
		const { result } = renderHook(() => usePersistentSurface("main"));
		expect(result.current.surfaceJson).toBeNull();
		expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
	});
});
