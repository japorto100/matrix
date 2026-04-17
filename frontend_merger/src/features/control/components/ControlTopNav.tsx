"use client";

// ControlTopNav — Sub-nav for Control surface (Slice 7: Two-Tier Mode)
// User Mode (default): Overview · Agents · Permissions · Skills · Tools · Sessions · Security
// Developer Mode (add): System · API/Models · Sandbox · Audit · MCP · A2A
// Mode toggle rechts via ModeToggle component (URL param + localStorage, D20)

import {
	Activity,
	Boxes,
	FileSearch,
	LayoutDashboard,
	Network,
	Server,
	Settings2,
	Shield,
	ShieldCheck,
	Sparkles,
	Terminal,
	Users,
	Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useControlMode } from "../mode";
import { ModeToggle } from "./ModeToggle";

type Section = "user" | "dev";

interface SubTab {
	href: string;
	label: string;
	icon: React.ReactNode;
	match: (p: string) => boolean;
	section: Section;
}

const TABS: SubTab[] = [
	// ─── User Mode (default, visible to all) ──────────────────────────────
	{
		href: "/control",
		label: "Overview",
		icon: <LayoutDashboard className="h-3 w-3" />,
		match: (p) =>
			p === "/control" ||
			p === "/control/" ||
			p === "/control/overview" ||
			p === "/control/overview/",
		section: "user",
	},
	{
		href: "/control/agents",
		label: "Agents",
		icon: <Users className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/agents"),
		section: "user",
	},
	{
		href: "/control/permissions",
		label: "Permissions",
		icon: <Shield className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/permissions"),
		section: "user",
	},
	{
		href: "/control/skills",
		label: "Skills",
		icon: <Sparkles className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/skills"),
		section: "user",
	},
	{
		href: "/control/tools",
		label: "Tools",
		icon: <Boxes className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/tools"),
		section: "user",
	},
	{
		href: "/control/sessions",
		label: "Sessions",
		icon: <Activity className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/sessions"),
		section: "user",
	},
	{
		href: "/control/context",
		label: "Context",
		icon: <Network className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/context"),
		section: "user",
	},
	{
		href: "/control/security",
		label: "Security",
		icon: <ShieldCheck className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/security"),
		section: "user",
	},
	// ─── Developer Mode (admin only) ───────────────────────────────────────
	{
		href: "/control/system",
		label: "System",
		icon: <Server className="h-3 w-3" />,
		match: (p) =>
			p === "/control/system" ||
			(p.startsWith("/control/system") && !p.startsWith("/control/system/env")),
		section: "dev",
	},
	{
		href: "/control/api",
		label: "API/Models",
		icon: <Settings2 className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/api") || p.startsWith("/control/system/env"),
		section: "dev",
	},
	{
		href: "/control/sandbox",
		label: "Sandbox",
		icon: <Terminal className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/sandbox"),
		section: "dev",
	},
	{
		href: "/control/audit",
		label: "Audit",
		icon: <FileSearch className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/audit"),
		section: "dev",
	},
	{
		href: "/control/mcp",
		label: "MCP",
		icon: <Workflow className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/mcp"),
		section: "dev",
	},
	{
		href: "/control/a2a",
		label: "A2A",
		icon: <Workflow className="h-3 w-3" />,
		match: (p) => p.startsWith("/control/a2a"),
		section: "dev",
	},
];

export function ControlTopNav() {
	const pathname = usePathname();
	const { isDev } = useControlMode();

	const userTabs = TABS.filter((t) => t.section === "user");
	const devTabs = TABS.filter((t) => t.section === "dev");

	const renderTab = (tab: SubTab) => {
		const isActive = tab.match(pathname);
		return (
			<Link key={tab.href} href={tab.href}>
				<Button
					variant="ghost"
					size="sm"
					aria-current={isActive ? "page" : undefined}
					className={cn(
						"h-7 gap-1.5 px-2.5 text-xs font-medium",
						isActive
							? "bg-accent text-foreground"
							: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
					)}
				>
					{tab.icon}
					<span>{tab.label}</span>
				</Button>
			</Link>
		);
	};

	return (
		<nav className="flex items-center gap-1 px-6 py-2 border-b border-border bg-card/30 overflow-x-auto">
			{userTabs.map(renderTab)}

			{isDev && (
				<>
					<div className="h-5 w-px bg-border mx-1.5" aria-hidden />
					{devTabs.map(renderTab)}
				</>
			)}

			<div className="ml-auto pl-2 shrink-0">
				<ModeToggle />
			</div>
		</nav>
	);
}
