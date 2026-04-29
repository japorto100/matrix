import type { ResolvedMessage } from "@matrix/lib/types";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MessageBubble } from "./MessageContent";

afterEach(cleanup);

function resolvedWidget(overrides: Partial<ResolvedMessage> = {}): ResolvedMessage {
	return {
		eventId: "$widget",
		sender: "@alice:example.test",
		senderDisplayName: "alice",
		body: "[Widget: Status Board]",
		timestamp: 123,
		isOwn: false,
		isBot: false,
		isEdited: false,
		isRedacted: false,
		msgType: "m.widget",
		url: "https://widgets.example.test/board",
		...overrides,
	};
}

describe("MessageBubble widget rendering", () => {
	it("renders safe unapproved widget URLs as external links without embedding an iframe", () => {
		const { container } = render(<MessageBubble message={resolvedWidget()} />);

		const link = screen.getByRole("link", { name: /Widget in neuem Tab öffnen/ });
		expect(link.getAttribute("href")).toBe("https://widgets.example.test/board");
		expect(link.getAttribute("target")).toBe("_blank");
		expect(link.getAttribute("rel")).toContain("noopener");
		expect(container.querySelector("iframe")).toBeNull();
		expect(screen.getByText("fallback")).toBeTruthy();
	});

	it("renders approved policy widgets as passive mobile-compatible cards", () => {
		const { container } = render(
			<MessageBubble
				message={resolvedWidget({
					widget: {
						id: "status-board",
						name: "Status Board",
						type: "matrix-widget",
						url: "about:blank",
						origin: "null",
						status: "approved",
						permissions: ["read_room"],
						auditRefs: ["audit-approval"],
						isIframeAllowed: true,
						waitForIframeLoad: true,
					},
				})}
			/>,
		);

		expect(screen.getByText("approved")).toBeTruthy();
		expect(screen.getByRole("link", { name: /Widget in neuem Tab öffnen/ })).toBeTruthy();
		expect(container.querySelector("iframe")).toBeNull();
	});

	it("renders blocked widget URLs as passive text", () => {
		const { container } = render(
			<MessageBubble
				message={resolvedWidget({
					body: "[Widget: Bad Widget] (blocked URL)",
					url: undefined,
					widget: {
						id: "bad-widget",
						name: "Bad Widget",
						type: "matrix-widget",
						status: "blocked",
						blockedReason: "unsafe-widget-url",
						permissions: [],
						auditRefs: [],
						isIframeAllowed: false,
						waitForIframeLoad: true,
					},
				})}
			/>,
		);

		expect(screen.getByText("Bad Widget")).toBeTruthy();
		expect(screen.getByText("blocked")).toBeTruthy();
		expect(screen.getByText("unsafe-widget-url")).toBeTruthy();
		expect(container.querySelector("a")).toBeNull();
	});

	it("renders report artifact metadata on widget cards", () => {
		render(
			<MessageBubble
				message={resolvedWidget({
					widget: {
						id: "risk-brief",
						name: "Risk Brief",
						type: "matrix-widget",
						url: "https://widgets.example.test/reports/risk-brief",
						status: "approved",
						permissions: ["read_room"],
						auditRefs: ["audit-report-approval"],
						reportArtifact: {
							manifestId: "reports/risk-brief/manifest.json",
							outputPath: "reports/risk-brief/report.html",
							renderer: "markdown-fallback",
						},
						isIframeAllowed: true,
						waitForIframeLoad: true,
					},
				})}
			/>,
		);

		expect(screen.getByText("report reports/risk-brief/manifest.json")).toBeTruthy();
		expect(screen.getByText("reports/risk-brief/report.html")).toBeTruthy();
		expect(screen.getByText("markdown-fallback")).toBeTruthy();
	});
});
