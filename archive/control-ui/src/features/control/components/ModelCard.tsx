import { BrainCircuit, Check, Eye, Plus, SquareCode, Wrench } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ModelInfo } from "@/lib/queries/control";

export function formatPrice(perMtok: number | null | undefined): string {
	if (perMtok == null) return "\u2014";
	if (perMtok === 0) return "Free";
	if (perMtok < 0.1) return `$${perMtok.toFixed(3)}/Mtok`;
	if (perMtok < 10) return `$${perMtok.toFixed(2)}/Mtok`;
	return `$${perMtok.toFixed(0)}/Mtok`;
}

export function formatContext(ctx: number | undefined): string {
	if (!ctx) return "\u2014";
	if (ctx >= 1_000_000) return `${(ctx / 1_000_000).toFixed(1)}M`;
	if (ctx >= 1_000) return `${(ctx / 1_000).toFixed(0)}k`;
	return String(ctx);
}

export function ModelCard({
	model,
	isSelected,
	onToggle,
}: {
	model: ModelInfo;
	isSelected: boolean;
	onToggle: () => void;
}) {
	return (
		<Card className="hover:border-primary/50 transition-colors">
			<CardHeader className="pb-2">
				<div className="flex items-start justify-between gap-2">
					<div className="min-w-0 flex-1">
						<CardTitle className="truncate text-sm font-medium">{model.name}</CardTitle>
						<p className="text-muted-foreground mt-0.5 truncate text-xs">{model.id}</p>
					</div>
					<div className="flex items-center gap-1 shrink-0">
						{model.is_free && (
							<Badge variant="secondary" className="bg-green-500/10 text-green-600 text-xs">
								Free
							</Badge>
						)}
						<Button
							variant={isSelected ? "default" : "outline"}
							size="sm"
							className="h-6 w-6 p-0"
							onClick={onToggle}
						>
							{isSelected ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
						</Button>
					</div>
				</div>
			</CardHeader>
			<CardContent className="pt-0">
				<div className="mb-2 flex flex-wrap gap-1.5">
					{model.supports_tools && (
						<Badge variant="outline" className="gap-1 text-xs">
							<Wrench className="h-3 w-3" /> Tools
						</Badge>
					)}
					{model.supports_vision && (
						<Badge variant="outline" className="gap-1 text-xs">
							<Eye className="h-3 w-3" /> Vision
						</Badge>
					)}
					{model.supports_reasoning && (
						<Badge variant="outline" className="gap-1 text-xs">
							<BrainCircuit className="h-3 w-3" /> Reasoning
						</Badge>
					)}
					{model.supports_structured_output && (
						<Badge variant="outline" className="gap-1 text-xs">
							<SquareCode className="h-3 w-3" /> JSON
						</Badge>
					)}
				</div>
				<div className="text-muted-foreground flex items-center justify-between text-xs">
					<span>{formatContext(model.context_length)} ctx</span>
					<span>{formatPrice(model.prompt_price_per_mtok)}</span>
				</div>
			</CardContent>
		</Card>
	);
}
