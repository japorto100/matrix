import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentChatMarkdown } from "./AgentChatMarkdown";

describe("AgentChatMarkdown", () => {
	it("strips script tags and javascript URLs", () => {
		const { container } = render(
			<AgentChatMarkdown content={"hello <script>alert(1)</script> [bad](javascript:alert(1))"} />,
		);

		expect(container.querySelector("script")).toBeNull();
		expect(container.querySelector('a[href^="javascript:"]')).toBeNull();
		expect(container.textContent).toContain("hello");
	});
});
