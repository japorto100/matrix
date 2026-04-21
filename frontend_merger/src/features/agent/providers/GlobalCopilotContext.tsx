"use client";

import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useCurrentRoute } from "@agent/hooks/useCurrentRoute";
import { useGlobalChat } from "@agent/stores/globalChatStore";

interface Props {
	children: ReactNode;
}

/**
 * Inner component — CopilotKit hooks fire here. Only mounted when CopilotKit
 * provider is active (see outer gate below).
 */
function GlobalCopilotInner({ children }: Props) {
	const router = useRouter();
	const toggleChat = useGlobalChat((s) => s.toggleChat);
	const route = useCurrentRoute();

	useCopilotAction({
		name: "navigateTo",
		description: "Navigate the user to a specific route in the app",
		parameters: [
			{
				name: "route",
				type: "string",
				description: "Target route (e.g. /control/agents, /files, /memory/kg)",
				required: true,
			},
		],
		handler: async ({ route: target }: { route: string }) => {
			router.push(target);
			return { navigated: true, to: target };
		},
	});

	useCopilotAction({
		name: "toggleAgentSidebar",
		description: "Open or close the agent chat overlay",
		parameters: [],
		handler: async () => {
			toggleChat();
			return { toggled: true };
		},
	});

	useCopilotReadable({
		description: "The current route the user is viewing",
		value: route,
	});

	return <>{children}</>;
}

/**
 * Outer gate — when CopilotKit is disabled, renders children plain so the
 * CopilotKit hooks never fire without their provider.
 */
export function GlobalCopilotContext({ children }: Props) {
	const enabled = process.env.NEXT_PUBLIC_COPILOTKIT_ENABLED === "true";
	if (!enabled) return <>{children}</>;
	return <GlobalCopilotInner>{children}</GlobalCopilotInner>;
}
