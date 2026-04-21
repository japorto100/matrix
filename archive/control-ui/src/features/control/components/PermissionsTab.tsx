"use client";

// PermissionsTab — 6 roles × 7 tool categories grid
// Slice 5.2: D2 — DB Overlay + Hot-Reload pattern (5s TTL cache)
// K6 (Slice 5): Cell click cycles level via usePatchPermissionCell

import { useMemo } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import {
	usePatchPermissionCell,
	usePermissionMatrix,
	useResetPermissionCell,
	useToolCategories,
} from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockAgentRoles, mockPermissions, mockToolCategories } from "../mock-data";
import type { ConsentLevel, PermissionCell, ToolCategory, TradingRole } from "../types";

const LEVEL_COLOR: Record<ConsentLevel, string> = {
	auto: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
	inform: "bg-sky-500/20 text-sky-400 border-sky-500/30",
	confirm: "bg-amber-500/20 text-amber-400 border-amber-500/30",
	deny: "bg-rose-500/20 text-rose-400 border-rose-500/30",
};

const LEVEL_LABEL: Record<ConsentLevel, string> = {
	auto: "Auto",
	inform: "Inform",
	confirm: "Confirm",
	deny: "Deny",
};

// Cycle order: auto → inform → confirm → deny → auto
const LEVEL_CYCLE: Record<ConsentLevel, ConsentLevel> = {
	auto: "inform",
	inform: "confirm",
	confirm: "deny",
	deny: "auto",
};

export function PermissionsTab() {
	// Slice 7 Phase H: real backend with mock fallback
	const matrixQuery = usePermissionMatrix();
	const catsQuery = useToolCategories();
	const patchCell = usePatchPermissionCell();
	const resetCellMutation = useResetPermissionCell();
	const cells = (matrixQuery.data?.items as PermissionCell[] | undefined) ?? mockPermissions;
	const categories = (catsQuery.data?.items as ToolCategory[] | undefined) ?? mockToolCategories;

	const handleCellClick = async (cell: PermissionCell) => {
		const nextLevel = LEVEL_CYCLE[cell.level];
		try {
			await patchCell.mutateAsync({
				role_id: cell.role_id,
				category_id: cell.category_id,
				level: nextLevel,
			});
			toast.success(`${cell.role_id} · ${cell.category_id}: ${cell.level} → ${nextLevel}`);
		} catch (err) {
			toast.error(`Update failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	const handleCellRightClick = async (cell: PermissionCell, e: React.MouseEvent) => {
		e.preventDefault();
		if (!cell.is_overridden) {
			toast.info("Cell uses yaml default — nothing to reset");
			return;
		}
		try {
			await resetCellMutation.mutateAsync({
				roleId: cell.role_id,
				categoryId: cell.category_id,
			});
			toast.success(`Reset ${cell.role_id} · ${cell.category_id} to default`);
		} catch (err) {
			toast.error(`Reset failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	const matrix = useMemo(() => {
		const m: Record<string, Record<TradingRole, PermissionCell>> = {};
		for (const cell of cells) {
			if (!m[cell.category_id]) m[cell.category_id] = {} as never;
			m[cell.category_id]![cell.role_id] = cell;
		}
		return m;
	}, [cells]);

	const overrideCount = cells.filter((p) => p.is_overridden).length;

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Permission Matrix</h2>
					<p className="text-xs text-muted-foreground">
						{mockAgentRoles.length} roles × {categories.length} tool categories · {overrideCount}{" "}
						cells overridden
					</p>
				</div>
				<div className="flex items-center gap-3 text-[10px]">
					{(["auto", "inform", "confirm", "deny"] as ConsentLevel[]).map((level) => (
						<div key={level} className="flex items-center gap-1.5">
							<div className={cn("h-2.5 w-2.5 rounded-sm border", LEVEL_COLOR[level])} />
							<span className="text-muted-foreground capitalize">{level}</span>
						</div>
					))}
				</div>
			</header>

			<div className="rounded-lg border border-border overflow-hidden">
				<table className="w-full text-xs">
					<thead className="bg-card/40">
						<tr>
							<th className="text-left py-2 px-3 font-semibold border-r border-border">
								Tool Category
							</th>
							{mockAgentRoles.map((role) => (
								<th
									key={role.id}
									className="text-center py-2 px-2 font-semibold border-r border-border last:border-r-0"
									title={role.display_name}
								>
									<div className="text-[10px] font-medium leading-tight">
										{role.display_name.split(" ").map((w) => (
											<div key={w}>{w}</div>
										))}
									</div>
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{categories.map((cat) => (
							<tr key={cat.id} className="border-t border-border hover:bg-card/20">
								<td className="py-2 px-3 border-r border-border">
									<div className="font-medium">{cat.display_name}</div>
									<div className="text-[10px] text-muted-foreground font-mono mt-0.5">
										{cat.tools.length} tools
									</div>
								</td>
								{mockAgentRoles.map((role) => {
									const cell = matrix[cat.id]?.[role.id];
									if (!cell) {
										return <td key={role.id} className="border-r border-border last:border-r-0" />;
									}
									return (
										<td
											key={role.id}
											className="py-2 px-2 text-center border-r border-border last:border-r-0 cursor-pointer hover:opacity-80 transition-opacity"
											title={`${role.display_name} → ${cat.display_name}: ${LEVEL_LABEL[cell.level]}${cell.is_overridden ? " (overridden, right-click to reset)" : ""}`}
											onClick={() => handleCellClick(cell)}
											onContextMenu={(e) => handleCellRightClick(cell, e)}
										>
											<div className="flex flex-col items-center gap-1">
												<Badge
													variant="outline"
													className={cn("text-[10px] h-5 px-2", LEVEL_COLOR[cell.level])}
												>
													{LEVEL_LABEL[cell.level]}
												</Badge>
												{cell.is_overridden && (
													<div
														className="h-1 w-1 rounded-full bg-amber-400"
														title="DB overlay (overrides yaml default)"
													/>
												)}
											</div>
										</td>
									);
								})}
							</tr>
						))}
					</tbody>
				</table>
			</div>

			<div className="text-[11px] text-muted-foreground space-y-1">
				<p>
					<span className="text-foreground font-medium">Click cell:</span> cycle level (auto →
					inform → confirm → deny → auto)
				</p>
				<p>
					<span className="text-foreground font-medium">Right-click cell:</span> reset overlay →
					yaml default
				</p>
				<p>
					<span className="text-foreground font-medium">Amber dot:</span> DB overlay (overrides yaml
					default from <code className="font-mono">consent_policy.yaml</code>)
				</p>
			</div>
		</div>
	);
}
