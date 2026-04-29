import type { ResolvedMessage } from "@matrix/lib/types";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MessageBubble } from "./MessageContent";

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
	it("renders safe widget URLs as external links without embedding an iframe", () => {
		const { container } = render(<MessageBubble message={resolvedWidget()} />);

		const link = screen.getByRole("link", { name: /\[Widget: Status Board\]/ });
		expect(link.getAttribute("href")).toBe("https://widgets.example.test/board");
		expect(link.getAttribute("target")).toBe("_blank");
		expect(link.getAttribute("rel")).toContain("noopener");
		expect(container.querySelector("iframe")).toBeNull();
	});

	it("renders blocked widget URLs as passive text", () => {
		const { container } = render(
			<MessageBubble
				message={resolvedWidget({
					body: "[Widget: Bad Widget] (blocked URL)",
					url: undefined,
				})}
			/>,
		);

		expect(screen.getByText("[Widget: Bad Widget] (blocked URL)")).toBeTruthy();
		expect(container.querySelector("a")).toBeNull();
	});
});
