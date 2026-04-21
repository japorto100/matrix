"use client";

// MemoryTopNav — Sub-nav for Memory surface
// Tabs: Episodes (default) · Graph (Episode-Memory) · KG (Trading) · Timeline · Ingestion
// URL is source of truth via usePathname.

import { Brain, Clock, FileUp, GitGraph, Network } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SubTab {
	href: string;
	label: string;
	icon: React.ReactNode;
	match: (p: string) => boolean;
}

const TABS: SubTab[] = [
	{
		href: "/memory",
		label: "Episodes",
		icon: <Brain className="h-3 w-3" />,
		match: (p) => p === "/memory" || p === "/memory/",
	},
	{
		href: "/memory/timeline",
		label: "Timeline",
		icon: <Clock className="h-3 w-3" />,
		match: (p) => p.startsWith("/memory/timeline"),
	},
	{
		href: "/memory/graph",
		label: "Provenance",
		icon: <GitGraph className="h-3 w-3" />,
		match: (p) => p.startsWith("/memory/graph"),
	},
	{
		href: "/memory/kg",
		label: "Knowledge Graph",
		icon: <Network className="h-3 w-3" />,
		match: (p) => p.startsWith("/memory/kg"),
	},
	{
		href: "/memory/ingestion",
		label: "Ingestion",
		icon: <FileUp className="h-3 w-3" />,
		match: (p) => p.startsWith("/memory/ingestion"),
	},
];

export function MemoryTopNav() {
	const pathname = usePathname();

	return (
		<nav className="flex items-center gap-1 px-6 py-2 border-b border-border bg-card/30">
			{TABS.map((tab) => {
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
			})}
		</nav>
	);
}
