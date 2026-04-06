"use client";

// GlobalTopBar — persistent surface-level navigation (SOTA 2026, 40px)
// Visible on all shell surfaces: /trading, /geopolitical-map, /control, /files

import {
	BarChart3,
	Clock,
	FolderOpen,
	Globe,
	Newspaper,
	SlidersHorizontal,
	TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { UserMenuButton } from "@/components/UserMenuButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useGlobalChat } from "@/features/agent-chat/context/GlobalChatContext";
import { AlertPanel } from "@/features/settings/alerts/AlertPanel";
import { ThemePicker } from "@/features/settings/ThemePicker";
import { cn } from "@/lib/utils";

interface SurfaceLink {
	href: string;
	label: string;
	icon: React.ReactNode;
	match: (pathname: string) => boolean;
}

const SURFACES: SurfaceLink[] = [
	{
		href: "/trading",
		label: "Trading",
		icon: <TrendingUp className="h-3.5 w-3.5" />,
		match: (p) => p === "/trading" || p === "/",
	},
	{
		href: "/research",
		label: "Research",
		icon: <Newspaper className="h-3.5 w-3.5" />,
		match: (p) => p.startsWith("/research"),
	},
	{
		href: "/geopolitical-map",
		label: "Map",
		icon: <Globe className="h-3.5 w-3.5" />,
		match: (p) => p.startsWith("/geopolitical-map"),
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
	const { open: chatOpen, badgeCount, toggleChat } = useGlobalChat();
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
			{/* Left: logo + surface switcher */}
			<nav aria-label="Primary surfaces" className="flex items-center gap-1">
				<Link
					href="/trading"
					className="flex items-center gap-1.5 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-md px-2 py-1 hover:opacity-90 transition-opacity mr-2"
					aria-label="Open trading workspace"
				>
					<BarChart3 className="h-4 w-4 text-white" />
					<span className="font-bold text-white text-sm hidden sm:inline">TradeView</span>
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

			{/* Right: clock + alerts + settings + AI chat + user + theme */}
			<div className="flex items-center gap-1">
				<Badge
					variant="outline"
					className="h-6 gap-1 font-mono text-[11px] bg-background/50 hidden md:flex"
				>
					<Clock className="h-3 w-3" />
					{clockTime}
				</Badge>

				<Separator orientation="vertical" className="h-5 mx-1" />

				<AlertPanel />

				<UserMenuButton />
				<ThemePicker />

				<Separator orientation="vertical" className="h-5 mx-1" />

				{/* AC75/AC77/AC88: AI Chat toggle — ⌘L + proactive badge */}
				<div className="relative">
					<Button
						variant="ghost"
						size="icon"
						className={cn(
							"h-8 w-8 transition-all rounded-lg border",
							chatOpen
								? "bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/50"
								: "border-white/20 hover:border-white/40 hover:bg-accent/50",
						)}
						onClick={toggleChat}
						title="AI Agent Chat (⌘L)"
						aria-label="Toggle AI chat"
					>
						<img
							src="/chatbot.png"
							alt="AI Chat"
							className={cn(
								"h-5 w-5 transition-opacity invert",
								chatOpen ? "opacity-100" : "opacity-60",
							)}
						/>
					</Button>
					{badgeCount > 0 && !chatOpen && (
						<span className="pointer-events-none absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-500 text-[8px] font-bold text-white animate-pulse">
							{badgeCount > 9 ? "9+" : badgeCount}
						</span>
					)}
				</div>
			</div>
		</header>
	);
}
