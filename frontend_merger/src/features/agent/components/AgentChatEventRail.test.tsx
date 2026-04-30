import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentChatEventRail } from "./AgentChatEventRail";

describe("AgentChatEventRail", () => {
	it("renders degradation flags, source layer counts and context pressure", () => {
		render(
			<AgentChatEventRail
				status="live"
				isStreaming={true}
				contextPressure={0.76}
				degradationFlags={[
					"NO_WORLD_KG",
					"NO_WORLD_EVIDENCE",
					"NO_PERSONAL_MEMORY",
					"NO_PERSONAL_KB",
					"WORLD_CLAIM_CONFLICT",
				]}
				sourceLayerCounts={{ personal_memory: 2, web: 1, empty: 0 }}
			/>,
		);

		expect(screen.getByText("NO_WORLD_KG")).toBeTruthy();
		expect(screen.getByText("NO_WORLD_EVIDENCE")).toBeTruthy();
		expect(screen.getByText("NO_PERSONAL_MEMORY")).toBeTruthy();
		expect(screen.getByText("NO_PERSONAL_KB")).toBeTruthy();
		expect(screen.getByText("WORLD_CLAIM_CONFLICT")).toBeTruthy();
		expect(screen.getByText("personal_memory:2 web:1")).toBeTruthy();
		expect(screen.getByText("76% ctx")).toBeTruthy();
	});

	it("renders runtime and request telemetry summaries", () => {
		render(
			<AgentChatEventRail
				status="live"
				isStreaming={false}
				requestTelemetry={[
					{
						cache_break_reasons: ["first_request"],
						usage: { unknown_fields: ["cache_write_tokens"] },
					},
				]}
				runtimeEvents={[{ kind: "llm", status: "completed" }]}
			/>,
		);

		expect(screen.getByText("1 evt completed")).toBeTruthy();
		expect(screen.getByText("cache:first_request")).toBeTruthy();
		expect(screen.getByText("unknown:cache_write_tokens")).toBeTruthy();
	});
});
