"use client";

// GlobalTopBar — persistent surface-level navigation (40px)
// Visible on all shell surfaces: /memory, /control, /files
// Adopted from D:/matrix/control/control_surface/src/components/GlobalTopBar.tsx,
// stripped of tradeview-fusion deps (AgentChat, AlertPanel, ThemePicker, UserMenu).

import { Brain, Clock, FolderOpen, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface SurfaceLink {
	href: string;
	label: string;
	icon: React.ReactNode;
	match: (pathname: string) => boolean;
}

const SURFACES: SurfaceLink[] = [
	{
		href: "/memory",
		label: "Memory",
		icon: <Brain className="h-3.5 w-3.5" />,
		match: (p) => p === "/" || p.startsWith("/memory"),
	},
	{
		href: "/control",
		label: "Control",
		icon: <SlidersHorizontal className="h-3.5 w-3.5" />,
		match: (p) => p.startsWith("/control"),
	},
	{
		href: "/files",
		label: "Files",
		icon: <FolderOpen className="h-3.5 w-3.5" />,
		match: (p) => p.startsWith("/files"),
	},
];

export function GlobalTopBar() {
	const pathname = usePathname();
	const [clockTime, setClockTime] = useState("");

	useEffect(() => {
		setClockTime(new Date().toLocaleTimeString());
		const timer = window.setInterval(() => {
			setClockTime(new Date().toLocaleTimeString());
		}, 1000);
		return () => window.clearInterval(timer);
	}, []);

	return (
		<header className="flex h-10 shrink-0 items-center justify-between border-b border-border bg-card px-3 gap-4">
			{/* Left: brand + surface switcher */}
			<nav aria-label="Primary surfaces" className="flex items-center gap-1">
				<Link
					href="/memory"
					className="flex items-center gap-1.5 rounded-md px-2 py-1 hover:opacity-90 transition-opacity mr-2"
					aria-label="Open memory surface"
				>
					<Brain className="h-4 w-4 text-primary" />
					<span className="font-bold text-sm hidden sm:inline">
						Matrix <span className="text-muted-foreground">· Control</span>
					</span>
				</Link>

				{SURFACES.map((surface) => {
					const isActive = surface.match(pathname);
					return (
						<Link
							key={surface.href}
							href={surface.href}
							data-testid={`link-${surface.label.toLowerCase()}`}
						>
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
								{surface.icon}
								<span>{surface.label}</span>
							</Button>
						</Link>
					);
				})}
			</nav>

			{/* Right: clock (placeholder for future: alerts, settings, user) */}
			<div className="flex items-center gap-1">
				<Badge
					variant="outline"
					className="h-6 gap-1 font-mono text-[11px] bg-background/50 hidden md:flex"
				>
					<Clock className="h-3 w-3" />
					{clockTime}
				</Badge>

				<Separator orientation="vertical" className="h-5 mx-1" />

				<span className="text-xs text-muted-foreground hidden lg:inline">local · dev</span>
			</div>
		</header>
	);
}
