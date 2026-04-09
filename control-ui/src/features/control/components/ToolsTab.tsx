"use client";

// ToolsTab — registry of all tools (builtin + MCP + skills + A2A)
// Slice 5.5 (NEU coverage gap): Tools Registry Browser

import { Network, Package, Sparkles, Workflow } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useTools } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockTools } from "../mock-data";
import type { ToolDefinition, ToolType } from "../types";

const TYPE_ICON: Record<ToolType, React.ReactNode> = {
	builtin: <Package className="h-3 w-3" />,
	mcp: <Network className="h-3 w-3" />,
	skill: <Sparkles className="h-3 w-3" />,
	a2a: <Workflow className="h-3 w-3" />,
};

const TYPE_COLOR: Record<ToolType, string> = {
	builtin: "border-sky-500/50 text-sky-400",
	mcp: "border-purple-500/50 text-purple-400",
	skill: "border-amber-500/50 text-amber-400",
	a2a: "border-emerald-500/50 text-emerald-400",
};

export function ToolsTab() {
	const [filter, setFilter] = useState("");
	const [typeFilter, setTypeFilter] = useState<ToolType | "all">("all");

	// Slice 7 Phase H: real backend with mock fallback
	const query = useTools();
	const allTools = (query.data?.items as ToolDefinition[] | undefined) ?? mockTools;

	const filtered = useMemo(() => {
		return allTools.filter((tool) => {
			if (typeFilter !== "all" && tool.type !== typeFilter) return false;
			if (filter && !tool.name.toLowerCase().includes(filter.toLowerCase())) return false;
			return true;
		});
	}, [allTools, filter, typeFilter]);

	const counts = allTools.reduce<Record<ToolType, number>>(
		(acc, t) => {
			acc[t.type] = (acc[t.type] ?? 0) + 1;
			return acc;
		},
		{ builtin: 0, mcp: 0, skill: 0, a2a: 0 },
	);

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Tools Registry</h2>
					<p className="text-xs text-muted-foreground">
						{allTools.length} tools · {counts.builtin} builtin · {counts.mcp} MCP · {counts.skill}{" "}
						skill · {counts.a2a} A2A
					</p>
				</div>
				<div className="flex items-center gap-2">
					<Input
						placeholder="Search tools..."
						value={filter}
						onChange={(e) => setFilter(e.target.value)}
						className="h-8 w-48 text-xs"
					/>
					<Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as ToolType | "all")}>
						<SelectTrigger className="h-8 w-32 text-xs">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All types</SelectItem>
							<SelectItem value="builtin">Builtin</SelectItem>
							<SelectItem value="mcp">MCP</SelectItem>
							<SelectItem value="skill">Skill</SelectItem>
							<SelectItem value="a2a">A2A</SelectItem>
						</SelectContent>
					</Select>
				</div>
			</header>

			<div className="rounded-lg border border-border overflow-hidden">
				<table className="w-full text-xs">
					<thead className="bg-card/40">
						<tr className="text-left">
							<th className="py-2 px-3 font-semibold w-20">Type</th>
							<th className="py-2 px-3 font-semibold">Name</th>
							<th className="py-2 px-3 font-semibold">Description</th>
							<th className="py-2 px-3 font-semibold w-24">Provider</th>
							<th className="py-2 px-3 font-semibold w-20 text-right">Calls 24h</th>
							<th className="py-2 px-3 font-semibold w-20 text-right">Avg ms</th>
							<th className="py-2 px-3 font-semibold w-16 text-center">Enabled</th>
						</tr>
					</thead>
					<tbody>
						{filtered.map((tool) => (
							<tr key={tool.id} className="border-t border-border hover:bg-card/20">
								<td className="py-2 px-3">
									<Badge
										variant="outline"
										className={cn("text-[10px] h-5 gap-1 px-1.5", TYPE_COLOR[tool.type])}
									>
										{TYPE_ICON[tool.type]}
										{tool.type}
									</Badge>
								</td>
								<td className="py-2 px-3">
									<div className="font-mono text-[11px]">{tool.name}</div>
									<div className="text-[10px] text-muted-foreground font-mono mt-0.5 line-clamp-1">
										{tool.input_schema_summary}
									</div>
								</td>
								<td className="py-2 px-3">
									<div className="line-clamp-2 leading-relaxed text-muted-foreground">
										{tool.description}
									</div>
									<div className="flex flex-wrap gap-1 mt-1">
										{tool.categories.map((cat) => (
											<Badge key={cat} variant="secondary" className="text-[9px] h-4 px-1.5">
												{cat}
											</Badge>
										))}
									</div>
								</td>
								<td className="py-2 px-3 text-[10px] text-muted-foreground">
									{tool.provider ?? "—"}
								</td>
								<td className="py-2 px-3 text-right font-mono">{tool.call_count_24h}</td>
								<td className="py-2 px-3 text-right font-mono text-muted-foreground">
									{tool.avg_latency_ms ?? "—"}
								</td>
								<td className="py-2 px-3 text-center">
									<Switch checked={tool.enabled} disabled />
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>

			{filtered.length === 0 && (
				<div className="text-xs text-muted-foreground text-center py-8 border border-dashed border-border rounded-lg">
					No tools match filters
				</div>
			)}
		</div>
	);
}
