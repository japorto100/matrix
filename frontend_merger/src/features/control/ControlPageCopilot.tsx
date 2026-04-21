"use client";

/**
 * ControlPageCopilot — CopilotKit action/readable registration for the
 * /control surface. Env-gated; no-op unless NEXT_PUBLIC_COPILOTKIT_ENABLED.
 *
 * Exposes:
 *   - readable "activeControlTab" — the sub-route under /control
 *   - action "openControlTab" — navigate router to /control/<tab>
 */

import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { usePathname, useRouter } from "next/navigation";

const KNOWN_TABS = [
	"overview",
	"agents",
	"permissions",
	"skills",
	"tools",
	"sessions",
	"tasks",
	"context",
	"security",
	"system",
	"sandbox",
	"audit",
	"mcp",
	"a2a",
	"api",
] as const;

function ControlCopilotInner() {
	const router = useRouter();
	const pathname = usePathname();
	const activeControlTab = pathname.startsWith("/control/")
		? (pathname.split("/")[2] ?? "overview")
		: "overview";

	useCopilotReadable({
		description: `Currently active Control-UI tab. One of: ${KNOWN_TABS.join(", ")}.`,
		value: { activeControlTab },
	});

	useCopilotAction({
		name: "openControlTab",
		description: "Switch to a specific tab inside the Control UI",
		parameters: [
			{
				name: "tab",
				type: "string",
				description: `One of: ${KNOWN_TABS.join(", ")}`,
				required: true,
			},
		],
		handler: async ({ tab }: { tab: string }) => {
			const allowed = (KNOWN_TABS as readonly string[]).includes(tab);
			if (!allowed) return { switched: false, error: `unknown tab: ${tab}` };
			router.push(tab === "overview" ? "/control" : `/control/${tab}`);
			return { switched: true, tab };
		},
	});

	return null;
}

export function ControlPageCopilot() {
	const enabled = process.env.NEXT_PUBLIC_COPILOTKIT_ENABLED === "true";
	if (!enabled) return null;
	return <ControlCopilotInner />;
}
