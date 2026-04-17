"use client";

// GlobalTopBar — 40px persistente Shell-Navigation fuer frontend_merger.
//
// Adaptiert aus control-ui/src/components/GlobalTopBar.tsx und
// control/control_surface/src/components/GlobalTopBar.tsx (tradeview-fusion).
//
// Drei Surfaces:
//   [Matrix]  → Link auf /matrix (Fullscreen Matrix Chat)
//   [Agent]   → Toggle der GlobalChatOverlay Sheet/Split/Rail (kein Route-Change)
//   [Control] → Link auf /control (Fullscreen Control UI)

import { Bot, Clock, MessageSquare, SlidersHorizontal, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useGlobalChat } from "@/features/agent/stores/globalChatStore";
import { cn } from "@/lib/utils";

interface NavLink {
	href: string;
	label: string;
	icon: React.ReactNode;
	match: (pathname: string) => boolean;
}

const NAV_LINKS: NavLink[] = [
	{
		href: "/matrix",
		label: "Matrix",
		icon: <MessageSquare className="h-3.5 w-3.5" />,
		match: (p) => p.startsWith("/matrix"),
	},
	{
		href: "/control",
		label: "Control",
		icon: <SlidersHorizontal className="h-3.5 w-3.5" />,
		match: (p) => p.startsWith("/control"),
	},
];

export function GlobalTopBar() {
	const pathname = usePathname();
	const chatOpen = useGlobalChat((s) => s.open);
	const badgeCount = useGlobalChat((s) => s.badgeCount);
	const toggleChat = useGlobalChat((s) => s.toggleChat);
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
			<nav aria-label="Primary surfaces" className="flex items-center gap-1">
				<Link
					href="/"
					className="flex items-center gap-1.5 rounded-md px-2 py-1 hover:opacity-90 transition-opacity mr-2"
					aria-label="frontend_merger home"
				>
					<Sparkles className="h-4 w-4 text-primary" />
					<span className="font-bold text-sm hidden sm:inline">
						Matrix <span className="text-muted-foreground">· Merger</span>
					</span>
				</Link>

				{NAV_LINKS.map((link) => {
					const isActive = link.match(pathname);
					return (
						<Link key={link.href} href={link.href} data-testid={`link-${link.label.toLowerCase()}`}>
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
								{link.icon}
								<span>{link.label}</span>
							</Button>
						</Link>
					);
				})}

				<Button
					variant="ghost"
					size="sm"
					onClick={toggleChat}
					data-testid="link-agent"
					aria-pressed={chatOpen}
					className={cn(
						"relative h-7 gap-1.5 px-2.5 text-xs font-medium",
						chatOpen
							? "bg-emerald-500/10 text-foreground border border-emerald-500/50"
							: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
					)}
					title="Toggle Agent Chat (⌘L)"
				>
					<Bot className="h-3.5 w-3.5" />
					<span>Agent</span>
					{badgeCount > 0 && !chatOpen && (
						<span className="pointer-events-none absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-500 text-[8px] font-bold text-white animate-pulse">
							{badgeCount > 9 ? "9+" : badgeCount}
						</span>
					)}
				</Button>
			</nav>

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
