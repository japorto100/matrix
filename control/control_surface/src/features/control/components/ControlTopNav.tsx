"use client";

// Control top nav — URL-driven subtab navigation (AC3, AC4, AC.V3)
// URL is source of truth; reload-stable, deep-link-capable.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavTab {
	href: string;
	label: string;
}

const TABS: NavTab[] = [
	{ href: "/control/overview", label: "Overview" },
	{ href: "/control/sessions", label: "Sessions" },
	{ href: "/control/tool-events", label: "Tool Events" },
	{ href: "/control/memory", label: "Memory" },
	{ href: "/control/kg-context", label: "KG / Context" },
	{ href: "/control/security", label: "Security" },
	{ href: "/control/skills", label: "Skills" },
	{ href: "/control/agents", label: "Agents" },
	{ href: "/control/evals", label: "Evals" },
];

export function ControlTopNav() {
	const pathname = usePathname();

	return (
		<nav
			className="flex items-center gap-0.5 overflow-x-auto border-b border-border bg-card/50 px-3 py-1 shrink-0"
			aria-label="Control navigation"
		>
			{TABS.map((tab) => {
				const isActive = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
				return (
					<Link key={tab.href} href={tab.href}>
						<span
							className={cn(
								"inline-flex h-7 items-center rounded px-2.5 text-xs font-medium transition-colors whitespace-nowrap",
								isActive
									? "bg-accent text-foreground"
									: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
							)}
						>
							{tab.label}
						</span>
					</Link>
				);
			})}
		</nav>
	);
}
