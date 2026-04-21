import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useCopilotActionMock = vi.fn();
const useCopilotReadableMock = vi.fn();

vi.mock("@copilotkit/react-core", () => ({
	useCopilotAction: (...args: unknown[]) => useCopilotActionMock(...args),
	useCopilotReadable: (...args: unknown[]) => useCopilotReadableMock(...args),
}));
vi.mock("next/navigation", () => ({
	usePathname: () => "/",
	useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@agent/stores/globalChatStore", () => ({
	useGlobalChat: (selector: (s: { toggleChat: () => void }) => unknown) =>
		selector({ toggleChat: vi.fn() }),
}));

import { GlobalCopilotContext } from "../GlobalCopilotContext";

describe("GlobalCopilotContext", () => {
	beforeEach(() => {
		useCopilotActionMock.mockClear();
		useCopilotReadableMock.mockClear();
	});
	afterEach(() => {
		delete (process.env as Record<string, string | undefined>).NEXT_PUBLIC_COPILOTKIT_ENABLED;
	});

	it("does NOT register hooks when env disabled", () => {
		(process.env as Record<string, string>).NEXT_PUBLIC_COPILOTKIT_ENABLED = "false";
		render(<GlobalCopilotContext>child</GlobalCopilotContext>);
		expect(useCopilotActionMock).not.toHaveBeenCalled();
		expect(useCopilotReadableMock).not.toHaveBeenCalled();
	});

	it("registers navigateTo + toggleAgentSidebar + currentRoute when env enabled", () => {
		(process.env as Record<string, string>).NEXT_PUBLIC_COPILOTKIT_ENABLED = "true";
		render(<GlobalCopilotContext>child</GlobalCopilotContext>);
		expect(useCopilotActionMock).toHaveBeenCalledWith(
			expect.objectContaining({ name: "navigateTo" }),
		);
		expect(useCopilotActionMock).toHaveBeenCalledWith(
			expect.objectContaining({ name: "toggleAgentSidebar" }),
		);
		expect(useCopilotReadableMock).toHaveBeenCalledWith(
			expect.objectContaining({ description: expect.stringContaining("current route") }),
		);
	});
});
