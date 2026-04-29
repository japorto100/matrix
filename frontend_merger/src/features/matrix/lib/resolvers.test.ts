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
				data: {
					audit_refs: ["audit-approval"],
					permissions: ["read_room"],
				},
			}),
			"@bob:example.test",
		);

		expect(message?.msgType).toBe("m.widget");
		expect(message?.body).toBe("[Widget: Status Board]");
		expect(message?.url).toBe("https://widgets.example.test/board?room=!abc");
		expect(message?.widget?.status).toBe("approved");
		expect(message?.widget?.isIframeAllowed).toBe(true);
		expect(message?.widget?.auditRefs).toEqual(["audit-approval"]);
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
		expect(message?.widget?.status).toBe("blocked");
		expect(message?.widget?.blockedReason).toBe("unsafe-widget-url");
	});

	it("keeps safe unapproved widgets as fallback-only", () => {
		const message = resolveMessage(
			matrixEvent("m.widget", {
				name: "Third Party Widget",
				url: "https://widgets.example.test/board",
			}),
			"@bob:example.test",
		);

		expect(message?.widget?.status).toBe("unsupported");
		expect(message?.widget?.isIframeAllowed).toBe(false);
	});

	it("preserves report artifact metadata for widget link handoff", () => {
		const message = resolveMessage(
			matrixEvent("m.widget", {
				name: "Risk Brief",
				url: "https://widgets.example.test/reports/risk-brief",
				data: {
					audit_refs: ["audit-report-approval"],
					report_manifest_id: "reports/risk-brief/manifest.json",
					report_output_path: "reports/risk-brief/report.html",
					report_renderer: "markdown-fallback",
				},
			}),
			"@bob:example.test",
		);

		expect(message?.widget?.status).toBe("approved");
		expect(message?.widget?.reportArtifact?.manifestId).toBe("reports/risk-brief/manifest.json");
		expect(message?.widget?.reportArtifact?.outputPath).toBe("reports/risk-brief/report.html");
		expect(message?.widget?.reportArtifact?.renderer).toBe("markdown-fallback");
	});
});
