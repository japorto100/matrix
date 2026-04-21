"use client";

// Files top nav — URL-driven tab navigation (DW3)
// URL is source of truth; reload-stable, deep-link-capable.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavTab {
	href: string;
	label: string;
}

const TABS: NavTab[] = [
	{ href: "/files/overview", label: "Overview" },
	{ href: "/files/documents", label: "Documents" },
	{ href: "/files/audio", label: "Audio" },
	{ href: "/files/video", label: "Video" },
	{ href: "/files/data", label: "Data" },
	{ href: "/files/images", label: "Images" },
	{ href: "/files/uploads", label: "Uploads" },
];

export function FilesTopNav() {
	const pathname = usePathname();

	return (
		<nav
			className="flex items-center gap-0.5 overflow-x-auto border-b border-border bg-card/50 px-3 py-1 shrink-0"
			aria-label="Files navigation"
		>
			{TABS.map((tab) => {
				const isActive =
					pathname === tab.href ||
					pathname.startsWith(`${tab.href}/`) ||
					(tab.href === "/files/overview" && pathname === "/files");
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
