"use client";

// EpisodeCard — Memory card preview for an Episode
// Pattern adapted from _ref/supermemory/apps/web/components/document-cards/note-preview.tsx
// (rounded card, header with icon, title with line-clamp, summary muted)
// Polymorphic via agent_role: each role gets its own color accent.

import { formatDistanceToNow } from "date-fns";
import { Brain, Coins, Newspaper, Shield, Sigma, TrendingUp } from "lucide-react";
import { memo } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getRoleColor, getRoleLabel } from "../mock-data";
import type { Episode } from "../types";

const ROLE_ICON: Record<Episode["agent_role"], typeof Brain> = {
	fundamentals_analyst: Coins,
	sentiment_analyst: Newspaper,
	technical_analyst: TrendingUp,
	researcher: Brain,
	trader: Sigma,
	risk_manager: Shield,
};

interface EpisodeCardProps {
	episode: Episode;
	onClick?: (episode: Episode) => void;
}

function EpisodeCardImpl({ episode, onClick }: EpisodeCardProps) {
	const Icon = ROLE_ICON[episode.agent_role];
	const roleColor = getRoleColor(episode.agent_role);
	const roleLabel = getRoleLabel(episode.agent_role);
	const confidencePercent = Math.round(episode.confidence * 100);

	return (
		<button
			type="button"
			onClick={() => onClick?.(episode)}
			className={cn(
				"w-full text-left bg-card hover:bg-accent/30 transition-colors",
				"border border-border/50 hover:border-border",
				"rounded-[18px] p-3.5 space-y-2.5",
				"focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
			)}
			style={{ boxShadow: "var(--shadow-card)" }}
		>
			{/* Header: role icon + label + confidence */}
			<div className="flex items-center justify-between gap-2">
				<div className="flex items-center gap-1.5 min-w-0">
					<div className="rounded-md p-1 shrink-0" style={{ backgroundColor: `${roleColor}25` }}>
						<Icon className="h-3.5 w-3.5" style={{ color: roleColor }} />
					</div>
					<p className="text-[11px] font-semibold truncate">{roleLabel}</p>
				</div>
				<Badge variant="outline" className="h-5 text-[9px] font-mono shrink-0 px-1.5">
					{confidencePercent}%
				</Badge>
			</div>

			{/* Input (truncated) */}
			<p className="text-[12px] font-semibold line-clamp-2 leading-[125%] text-foreground/95">
				{episode.input}
			</p>

			{/* Output preview (muted, line-clamped) */}
			<p className="text-[10px] text-muted-foreground line-clamp-3 leading-relaxed">
				{episode.output.replace(/[*#`]/g, "").substring(0, 200)}
			</p>

			{/* Footer: tags + time */}
			<div className="flex items-center justify-between gap-2 pt-1.5 border-t border-border/30">
				<div className="flex items-center gap-1 min-w-0 overflow-hidden">
					{episode.tags.slice(0, 3).map((tag) => (
						<span
							key={tag}
							className="text-[9px] px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground/90 font-mono shrink-0"
						>
							{tag}
						</span>
					))}
					{episode.tags.length > 3 && (
						<span className="text-[9px] text-muted-foreground/60 shrink-0">
							+{episode.tags.length - 3}
						</span>
					)}
				</div>
				<span className="text-[9px] font-mono text-muted-foreground/70 shrink-0">
					{formatDistanceToNow(new Date(episode.created_at), { addSuffix: true })}
				</span>
			</div>
		</button>
	);
}

export const EpisodeCard = memo(EpisodeCardImpl);
