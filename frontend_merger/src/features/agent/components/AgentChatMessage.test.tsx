import { cleanup, render, screen } from "@testing-library/react";
import type { UIMessage } from "ai";
import { afterEach, describe, expect, it } from "vitest";

import { AgentChatMessage } from "./AgentChatMessage";

afterEach(cleanup);

const baseProps = {
	onToggleBlock: () => undefined,
	collapsedTools: new Set<string>(),
};

describe("AgentChatMessage", () => {
	it("renders AI SDK static tool parts as tool blocks", () => {
		const message: UIMessage = {
			id: "assistant-1",
			role: "assistant",
			parts: [
				{
					type: "tool-get_weather",
					toolCallId: "tool-call-1",
					state: "output-available",
					input: { city: "Zurich" },
					output: { temperature: 12 },
				},
			],
		};

		render(<AgentChatMessage {...baseProps} message={message} />);

		expect(screen.getByText("get_weather")).toBeTruthy();
		expect(screen.getByText("done")).toBeTruthy();
		expect(screen.getByText(/Zurich/)).toBeTruthy();
		expect(screen.getByText(/temperature/)).toBeTruthy();
	});

	it("renders AI SDK dynamic tool parts as tool blocks", () => {
		const message: UIMessage = {
			id: "assistant-2",
			role: "assistant",
			parts: [
				{
					type: "dynamic-tool",
					toolName: "mcp_lookup",
					toolCallId: "tool-call-2",
					state: "output-error",
					input: { query: "risk" },
					errorText: "denied by policy",
				},
			],
		};

		render(<AgentChatMessage {...baseProps} message={message} />);

		expect(screen.getByText("mcp_lookup")).toBeTruthy();
		expect(screen.getByText("error")).toBeTruthy();
		expect(screen.getByText(/denied by policy/)).toBeTruthy();
	});
});
