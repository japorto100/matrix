import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentChatToolBlock } from "./AgentChatToolBlock";

describe("AgentChatToolBlock", () => {
	it("renders approval controls and forwards approve/deny decisions", async () => {
		const approve = vi.fn().mockResolvedValue(undefined);
		const deny = vi.fn().mockResolvedValue(undefined);

		render(
			<AgentChatToolBlock
				toolName="set_chart_state"
				toolCallId="call-1"
				state="approval-requested"
				input={{ symbol: "BTC/USD" }}
				isCollapsed={false}
				onToggle={() => undefined}
				onApprove={approve}
				onDeny={deny}
			/>,
		);

		expect(screen.getByText("Agent requests permission to run this tool")).toBeTruthy();

		fireEvent.click(screen.getByText("Approve"));
		await waitFor(() => expect(approve).toHaveBeenCalledWith("call-1"));

		fireEvent.click(screen.getByText("Deny"));
		await waitFor(() => expect(deny).toHaveBeenCalledWith("call-1"));
	});
});
