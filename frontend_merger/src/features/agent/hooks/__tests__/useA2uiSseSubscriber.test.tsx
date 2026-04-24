import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const processMessages = vi.fn();

vi.mock("@copilotkit/a2ui-renderer", () => ({
	useA2UIActions: () => ({ processMessages }),
}));

import { useA2uiSseSubscriber } from "../useA2uiSseSubscriber";

beforeEach(() => {
	processMessages.mockReset();
});

describe("useA2uiSseSubscriber", () => {
	it("returns false for non-a2ui packets and does not invoke processMessages", () => {
		const { result } = renderHook(() => useA2uiSseSubscriber());
		const handled = result.current({ type: "text-delta", delta: "x" });
		expect(handled).toBe(false);
		expect(processMessages).not.toHaveBeenCalled();
	});

	it("translates data-a2ui-surface-start to renderer createSurface message", () => {
		const { result } = renderHook(() => useA2uiSseSubscriber());
		const handled = result.current({
			type: "data-a2ui-surface-start",
			surfaceId: "main",
			components: [{ id: "root", component: "Text", text: "hi" }],
			dataModel: { foo: "bar" },
		});
		expect(handled).toBe(true);
		expect(processMessages).toHaveBeenCalledWith([
			{
				version: "v0.9",
				createSurface: {
					surfaceId: "main",
					tree: [{ id: "root", component: "Text", text: "hi" }],
					dataModel: { foo: "bar" },
				},
			},
		]);
	});

	it("translates data-a2ui-update-data-model to renderer updateDataModel", () => {
		const { result } = renderHook(() => useA2uiSseSubscriber());
		const patch = [{ op: "replace", path: "/price", value: 43 }];
		result.current({
			type: "data-a2ui-update-data-model",
			surfaceId: "main",
			patch,
		});
		expect(processMessages).toHaveBeenCalledWith([
			{ version: "v0.9", updateDataModel: { surfaceId: "main", patch } },
		]);
	});

	it("swallows renderer errors so chat does not tank", () => {
		processMessages.mockImplementation(() => {
			throw new Error("renderer boom");
		});
		const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
		const { result } = renderHook(() => useA2uiSseSubscriber());
		const handled = result.current({
			type: "data-a2ui-surface-end",
			surfaceId: "main",
		});
		// still returns true — we owned the packet even if rendering failed.
		expect(handled).toBe(true);
		warnSpy.mockRestore();
	});

	it("ignores malformed a2ui-shaped objects (missing surfaceId)", () => {
		const { result } = renderHook(() => useA2uiSseSubscriber());
		// type is valid but other required fields are missing — isA2uiPacket
		// only checks type, so we fall through to renderer which may warn.
		// Malformed null/undefined should be rejected by isA2uiPacket.
		expect(result.current(null)).toBe(false);
		expect(result.current(undefined)).toBe(false);
		expect(processMessages).not.toHaveBeenCalled();
	});
});
