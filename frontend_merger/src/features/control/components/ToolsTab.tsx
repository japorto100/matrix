"use client";

// ToolsTab — registry of all tools (builtin + MCP + skills + A2A)
// Slice 5.5 (NEU coverage gap): Tools Registry Browser

import { Network, Package, Plus, Shield, Sparkles, Workflow } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useAddToolFromUrl, useTools } from "@/lib/queries/hooks";
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

const RISK_COLOR: Record<NonNullable<ToolDefinition["risk"]>, string> = {
	low: "border-emerald-500/40 text-emerald-400",
	medium: "border-amber-500/40 text-amber-400",
	high: "border-orange-500/40 text-orange-400",
	critical: "border-rose-500/50 text-rose-400",
};

export function ToolsTab() {
	const [filter, setFilter] = useState("");
	const [typeFilter, setTypeFilter] = useState<ToolType | "all">("all");
	const [addOpen, setAddOpen] = useState(false);
	const [toolUrl, setToolUrl] = useState("");
	const [toolName, setToolName] = useState("");
	const [toolDescription, setToolDescription] = useState("");
	const [toolCategory, setToolCategory] = useState("");
	const addTool = useAddToolFromUrl();

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

	const handleAddTool = async () => {
		if (!toolUrl.trim()) return;
		try {
			const result = await addTool.mutateAsync({
				url: toolUrl.trim(),
				name: toolName.trim() || undefined,
				description: toolDescription.trim() || undefined,
				category: toolCategory.trim() || undefined,
			});
			toast.success(`Tool added: ${result.tool_id}`);
			setAddOpen(false);
			setToolUrl("");
			setToolName("");
			setToolDescription("");
			setToolCategory("");
		} catch (err) {
			toast.error(`Add tool failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

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
					<Button
						variant="outline"
						size="sm"
						className="h-8 gap-1.5 text-xs"
						onClick={() => setAddOpen(true)}
					>
						<Plus className="h-3 w-3" />
						Add Tool from URL
					</Button>
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
							<th className="py-2 px-3 font-semibold w-28">Policy</th>
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
										{tool.summary ?? tool.description ?? "—"}
									</div>
									<div className="flex flex-wrap gap-1 mt-1">
										{tool.categories.map((cat) => (
											<Badge key={cat} variant="secondary" className="text-[9px] h-4 px-1.5">
												{cat}
											</Badge>
										))}
									</div>
								</td>
								<td className="py-2 px-3">
									<div className="flex flex-wrap gap-1">
										{tool.risk && (
											<Badge
												variant="outline"
												className={cn("text-[9px] h-4 gap-1 px-1.5", RISK_COLOR[tool.risk])}
											>
												<Shield className="h-2.5 w-2.5" />
												{tool.risk}
											</Badge>
										)}
										{tool.approval && (
											<Badge variant="secondary" className="text-[9px] h-4 px-1.5">
												{tool.approval}
											</Badge>
										)}
										{tool.progressive_disclosure_level !== undefined && (
											<Badge variant="outline" className="text-[9px] h-4 px-1.5">
												L{tool.progressive_disclosure_level}
											</Badge>
										)}
									</div>
									{tool.policy_reasons && tool.policy_reasons.length > 0 && (
										<div className="mt-1 text-[10px] text-muted-foreground line-clamp-1">
											{tool.policy_reasons.join(", ")}
										</div>
									)}
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

			<Dialog open={addOpen} onOpenChange={setAddOpen}>
				<DialogContent className="sm:max-w-lg">
					<DialogHeader>
						<DialogTitle>Add Tool from URL</DialogTitle>
						<DialogDescription>
							Register a new URL-based tool for discovery and governance.
						</DialogDescription>
					</DialogHeader>
					<div className="space-y-3">
						<div className="space-y-1.5">
							<Label htmlFor="tool-url">Tool URL</Label>
							<Input
								id="tool-url"
								placeholder="https://example.com/mcp/tool-manifest.json"
								value={toolUrl}
								onChange={(e) => setToolUrl(e.target.value)}
							/>
						</div>
						<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
							<div className="space-y-1.5">
								<Label htmlFor="tool-name">Name (optional)</Label>
								<Input
									id="tool-name"
									placeholder="my-tool"
									value={toolName}
									onChange={(e) => setToolName(e.target.value)}
								/>
							</div>
							<div className="space-y-1.5">
								<Label htmlFor="tool-category">Category (optional)</Label>
								<Input
									id="tool-category"
									placeholder="market_data"
									value={toolCategory}
									onChange={(e) => setToolCategory(e.target.value)}
								/>
							</div>
						</div>
						<div className="space-y-1.5">
							<Label htmlFor="tool-description">Description (optional)</Label>
							<Textarea
								id="tool-description"
								className="min-h-[80px]"
								placeholder="What does this tool do?"
								value={toolDescription}
								onChange={(e) => setToolDescription(e.target.value)}
							/>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setAddOpen(false)}>
							Cancel
						</Button>
						<Button onClick={handleAddTool} disabled={!toolUrl.trim() || addTool.isPending}>
							{addTool.isPending ? "Adding..." : "Add Tool"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
