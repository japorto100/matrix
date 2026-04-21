import { describe, expect, it } from "vitest";
import { parseA2uiEnvelope } from "../a2uiTreeSchema";

describe("parseA2uiEnvelope", () => {
	it("accepts valid envelope with whitelisted root type", () => {
		const result = parseA2uiEnvelope({
			type: "a2ui",
			surface_id: "main",
			tree: { type: "Card", children: [{ type: "Text", text: "hello" }] },
		});
		expect(result.ok).toBe(true);
		if (result.ok) expect(result.surfaceId).toBe("main");
	});

	it("rejects wrong type field (Ansatz Y marker missing)", () => {
		const result = parseA2uiEnvelope({
			type: "other",
			surface_id: "main",
			tree: { type: "Card" },
		});
		expect(result.ok).toBe(false);
	});

	it("rejects unknown root component type (not in whitelist)", () => {
		const result = parseA2uiEnvelope({
			type: "a2ui",
			surface_id: "main",
			tree: { type: "NotAComponent" },
		});
		expect(result.ok).toBe(false);
	});

	it("rejects empty tree", () => {
		const result = parseA2uiEnvelope({
			type: "a2ui",
			surface_id: "main",
			tree: {},
		});
		expect(result.ok).toBe(false);
	});

	it("rejects JSON-string-not-object tree", () => {
		const result = parseA2uiEnvelope({
			type: "a2ui",
			surface_id: "main",
			tree: '{"type":"Card"}' as unknown as Record<string, unknown>,
		});
		expect(result.ok).toBe(false);
	});

	it("accepts nested valid children", () => {
		const result = parseA2uiEnvelope({
			type: "a2ui",
			surface_id: "chat-1",
			tree: {
				type: "Column",
				children: [
					{ type: "Card", children: [{ type: "Text", text: "NVDA" }] },
					{ type: "Row", children: [{ type: "Button", label: "Buy" }] },
				],
			},
		});
		expect(result.ok).toBe(true);
	});

	it("rejects child with unknown type in deep tree", () => {
		const result = parseA2uiEnvelope({
			type: "a2ui",
			surface_id: "main",
			tree: {
				type: "Card",
				children: [{ type: "Text" }, { type: "Evil" }],
			},
		});
		expect(result.ok).toBe(false);
	});
});
