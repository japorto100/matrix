"use client";

// EpisodeFilterBar — Filter pills for Episodes
// Pattern adopted 1:1 from _ref/supermemory/apps/web/components/memories-grid.tsx
// (filter-pills section, lines 411-450). Replaces categories with agent roles.

import { LayoutGrid, List, Loader, Sparkles, Table } from "lucide-react";
import { useQueryState } from "nuqs";
import { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { rolesParam, viewParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";
import { getRoleColor, getRoleLabel } from "../mock-data";
import type { AgentRoleId } from "../types";

const ROLES: AgentRoleId[] = [
	"researcher",
	"technical_analyst",
	"fundamentals_analyst",
	"sentiment_analyst",
	"trader",
	"risk_manager",
];

interface EpisodeFilterBarProps {
	totalCount?: number;
	roleCounts?: Partial<Record<AgentRoleId, number>>;
	isLoading?: boolean;
}

export function EpisodeFilterBar({
	totalCount,
	roleCounts = {},
	isLoading = false,
}: EpisodeFilterBarProps) {
	const [selectedRoles, setSelectedRoles] = useQueryState("roles", rolesParam);
	const [view, setView] = useQueryState("view", viewParam);

	const handleRoleToggle = useCallback(
		(role: AgentRoleId) => {
			setSelectedRoles((prev) => {
				const current = prev ?? [];
				if (current.includes(role)) {
					const next = current.filter((r) => r !== role);
					return next.length === 0 ? [] : next;
				}
				return [...current, role];
			});
		},
		[setSelectedRoles],
	);

	const handleSelectAll = useCallback(() => {
		setSelectedRoles([]);
	}, [setSelectedRoles]);

	return (
		<div id="filter-pills" className="flex items-center justify-between gap-4 px-6 mb-3">
			<div className="flex flex-wrap items-center gap-1.5">
				{/* "All" pill */}
				<Button
					className={cn(
						"rounded-full border border-border bg-card px-2.5 py-1 text-xs h-auto",
						"hover:bg-accent/60 hover:border-primary/30",
						selectedRoles.length === 0 && "bg-accent border-primary/40",
					)}
					onClick={handleSelectAll}
				>
					<Sparkles className="h-3 w-3 mr-1" />
					All
					{totalCount !== undefined && (
						<span className="ml-1 text-muted-foreground">({totalCount})</span>
					)}
				</Button>

				{/* Role pills */}
				{ROLES.map((role) => {
					const isSelected = selectedRoles.includes(role);
					const count = roleCounts[role];
					const color = getRoleColor(role);
					return (
						<Button
							key={role}
							className={cn(
								"rounded-full border border-border bg-card px-2.5 py-1 text-xs h-auto",
								"hover:bg-accent/60 hover:border-primary/30",
								isSelected && "bg-accent border-primary/40",
							)}
							style={
								isSelected
									? { borderColor: `${color}66`, backgroundColor: `${color}15` }
									: undefined
							}
							onClick={() => handleRoleToggle(role)}
						>
							<span
								className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
								style={{ backgroundColor: color }}
							/>
							{getRoleLabel(role)}
							{count !== undefined && <span className="ml-1 text-muted-foreground">({count})</span>}
						</Button>
					);
				})}

				{isLoading && <Loader className="h-3 w-3 animate-spin text-muted-foreground ml-1" />}
			</div>

			{/* View mode toggle (right side) */}
			<div className="flex items-center gap-1 shrink-0">
				<Button
					size="sm"
					variant={view === "grid" ? "secondary" : "ghost"}
					className="h-7 w-7 p-0"
					onClick={() => setView("grid")}
					aria-label="Grid view"
				>
					<LayoutGrid className="h-3.5 w-3.5" />
				</Button>
				<Button
					size="sm"
					variant={view === "table" ? "secondary" : "ghost"}
					className="h-7 w-7 p-0"
					onClick={() => setView("table")}
					aria-label="Table view"
				>
					<Table className="h-3.5 w-3.5" />
				</Button>
				<Button
					size="sm"
					variant={view === "timeline" ? "secondary" : "ghost"}
					className="h-7 w-7 p-0"
					onClick={() => setView("timeline")}
					aria-label="Timeline view"
				>
					<List className="h-3.5 w-3.5" />
				</Button>
			</div>
		</div>
	);
}
