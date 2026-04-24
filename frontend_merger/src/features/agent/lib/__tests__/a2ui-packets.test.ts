import { describe, expect, it } from "vitest";
import {
	type A2uiPacket,
	A2UI_PACKET_TYPES,
	isA2uiPacket,
	toRendererMessage,
} from "../a2ui-packets";

describe("isA2uiPacket", () => {
	it("accepts all five packet types", () => {
		for (const type of A2UI_PACKET_TYPES) {
			expect(isA2uiPacket({ type })).toBe(true);
		}
	});

	it("rejects foreign types (ai-sdk core packets)", () => {
		expect(isA2uiPacket({ type: "text-delta", delta: "x" })).toBe(false);
		expect(isA2uiPacket({ type: "tool-output-available" })).toBe(false);
		expect(isA2uiPacket({ type: "message-metadata" })).toBe(false);
	});

	it("rejects malformed values", () => {
		expect(isA2uiPacket(null)).toBe(false);
		expect(isA2uiPacket(undefined)).toBe(false);
		expect(isA2uiPacket("a2ui-surface-start")).toBe(false);
		expect(isA2uiPacket({})).toBe(false);
		expect(isA2uiPacket({ type: 123 })).toBe(false);
	});
});

describe("toRendererMessage", () => {
	it("maps surface-start to createSurface with tree + dataModel", () => {
		const packet: A2uiPacket = {
			type: "a2ui-surface-start",
			surfaceId: "main",
			components: { type: "Card" },
			dataModel: { price: 42 },
		};
		expect(toRendererMessage(packet)).toEqual({
			version: "v0.9",
			createSurface: { surfaceId: "main", tree: { type: "Card" }, dataModel: { price: 42 } },
		});
	});

	it("maps update-components to updateComponents", () => {
		const patch = [{ op: "add", path: "/x", value: 1 }];
		const packet: A2uiPacket = {
			type: "a2ui-update-components",
			surfaceId: "main",
			patch,
		};
		expect(toRendererMessage(packet)).toEqual({
			version: "v0.9",
			updateComponents: { surfaceId: "main", patch },
		});
	});

	it("maps update-data-model to updateDataModel", () => {
		const patch = [{ op: "replace", path: "/price", value: 43 }];
		const packet: A2uiPacket = {
			type: "a2ui-update-data-model",
			surfaceId: "main",
			patch,
		};
		expect(toRendererMessage(packet)).toEqual({
			version: "v0.9",
			updateDataModel: { surfaceId: "main", patch },
		});
	});

	it("maps surface-end and delete-surface to their terminal shapes", () => {
		expect(
			toRendererMessage({ type: "a2ui-surface-end", surfaceId: "main" }),
		).toEqual({ version: "v0.9", endSurface: { surfaceId: "main" } });

		expect(
			toRendererMessage({ type: "a2ui-delete-surface", surfaceId: "main" }),
		).toEqual({ version: "v0.9", deleteSurface: { surfaceId: "main" } });
	});
});
