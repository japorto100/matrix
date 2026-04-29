import type { MatrixEvent } from "matrix-js-sdk";
import { describe, expect, it } from "vitest";

import { resolveMessage } from "./resolvers";

function matrixEvent(type: string, content: Record<string, unknown>): MatrixEvent {
	return {
		getType: () => type,
		getContent: () => content,
		getSender: () => "@alice:example.test",
		getId: () => "$event",
		getTs: () => 123,
		isRedacted: () => false,
	} as unknown as MatrixEvent;
}

describe("resolveMessage widget events", () => {
	it("preserves safe widget URLs for the renderer", () => {
		const message = resolveMessage(
			matrixEvent("m.widget", {
				name: "Status Board",
				url: "https://widgets.example.test/board?room=!abc",
			}),
			"@bob:example.test",
		);

		expect(message?.msgType).toBe("m.widget");
		expect(message?.body).toBe("[Widget: Status Board]");
		expect(message?.url).toBe("https://widgets.example.test/board?room=!abc");
	});

	it("blocks non-http widget URLs", () => {
		const message = resolveMessage(
			matrixEvent("im.vector.modular.widgets", {
				name: "Bad Widget",
				url: "javascript:alert(1)",
			}),
			"@bob:example.test",
		);

		expect(message?.msgType).toBe("m.widget");
		expect(message?.body).toBe("[Widget: Bad Widget] (blocked URL)");
		expect(message?.url).toBeUndefined();
	});
});
