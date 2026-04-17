"use client";

// EpisodeDetailSheet — Right-side sheet showing full Episode details
// Pattern adapted from _ref/supermemory/apps/web/components/document-modal/index.tsx
// (Header + Title + Summary + Memory Relations + Delete button).
// Uses shadcn <Sheet> instead of Radix Dialog for better mobile UX.

import { format } from "date-fns";
import {
	Brain,
	Coins,
	Loader2,
	Newspaper,
	Shield,
	Sigma,
	Tag,
	Trash2,
	TrendingUp,
	Wrench,
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useDeleteEpisode } from "@/lib/queries/hooks";
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

interface EpisodeDetailSheetProps {
	episode: Episode | null;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

export function EpisodeDetailSheet({ episode, open, onOpenChange }: EpisodeDetailSheetProps) {
	const [confirmOpen, setConfirmOpen] = useState(false);
	const deleteEpisode = useDeleteEpisode();

	if (!episode) return null;

	const Icon = ROLE_ICON[episode.agent_role];
	const roleColor = getRoleColor(episode.agent_role);
	const roleLabel = getRoleLabel(episode.agent_role);
	const confidencePercent = Math.round(episode.confidence * 100);

	const handleDelete = async () => {
		try {
			await deleteEpisode.mutateAsync(episode.id);
			toast.success("Episode deleted");
			setConfirmOpen(false);
			onOpenChange(false);
		} catch (err) {
			toast.error(`Failed to delete: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	return (
		<Sheet open={open} onOpenChange={onOpenChange}>
			<SheetContent side="right" className="w-full sm:max-w-[600px] md:max-w-[720px] p-0 gap-0">
				<SheetHeader className="px-6 py-5 border-b border-border bg-card/50 space-y-3">
					<div className="flex items-center gap-2">
						<div
							className="rounded-md p-1.5 shrink-0"
							style={{ backgroundColor: `${roleColor}25` }}
						>
							<Icon className="h-4 w-4" style={{ color: roleColor }} />
						</div>
						<div className="min-w-0 flex-1">
							<SheetTitle className="text-sm font-semibold">{roleLabel}</SheetTitle>
							<SheetDescription className="text-[10px] font-mono text-muted-foreground">
								{episode.id} · session {episode.session_id} ·{" "}
								{format(new Date(episode.created_at), "PPpp")}
							</SheetDescription>
						</div>
						<Badge variant="outline" className="font-mono text-[10px]">
							{confidencePercent}% confidence
						</Badge>
					</div>

					{/* Tags */}
					<div className="flex items-center gap-1.5 flex-wrap">
						<Tag className="h-3 w-3 text-muted-foreground/70" />
						{episode.tags.map((tag) => (
							<span
								key={tag}
								className="text-[10px] px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground font-mono"
							>
								{tag}
							</span>
						))}
					</div>
				</SheetHeader>

				<ScrollArea className="flex-1 h-[calc(100vh-180px)]">
					<div className="px-6 py-5 space-y-6">
						{/* Input */}
						<section>
							<h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">
								Input
							</h3>
							<p className="text-sm leading-relaxed text-foreground/95 bg-muted/20 rounded-lg p-3">
								{episode.input}
							</p>
						</section>

						{/* Tool Calls */}
						{episode.tools_used.length > 0 && (
							<section>
								<h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
									<Wrench className="h-3 w-3" />
									Tool Calls ({episode.tools_used.length})
								</h3>
								<div className="space-y-1.5">
									{episode.tools_used.map((tool) => (
										<div
											key={tool}
											className="flex items-center justify-between gap-2 px-3 py-2 rounded-md bg-muted/20 border border-border/30"
										>
											<code className="text-[11px] font-mono text-foreground/90">{tool}</code>
											<Badge
												variant="outline"
												className="h-4 text-[9px] bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
											>
												ok
											</Badge>
										</div>
									))}
								</div>
							</section>
						)}

						{/* Output (markdown) */}
						<section>
							<h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">
								Output
							</h3>
							<div
								className={cn(
									"prose prose-sm prose-invert max-w-none",
									"prose-headings:font-semibold prose-headings:text-foreground",
									"prose-p:text-foreground/90 prose-p:leading-relaxed",
									"prose-strong:text-foreground prose-strong:font-semibold",
									"prose-ul:text-foreground/90 prose-li:text-foreground/90",
									"prose-code:text-foreground prose-code:bg-muted/40 prose-code:px-1 prose-code:rounded",
								)}
							>
								<ReactMarkdown remarkPlugins={[remarkGfm]}>{episode.output}</ReactMarkdown>
							</div>
						</section>

						{/* Stats */}
						<section className="grid grid-cols-3 gap-4 pt-4 border-t border-border/30">
							<div>
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
									Duration
								</p>
								<p className="text-sm font-bold tabular-nums mt-0.5">
									{(episode.duration_ms / 1000).toFixed(1)}s
								</p>
							</div>
							<div>
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
									Tokens
								</p>
								<p className="text-sm font-bold tabular-nums mt-0.5">
									{episode.token_count.toLocaleString()}
								</p>
							</div>
							<div>
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
									Created
								</p>
								<p className="text-sm font-bold mt-0.5">
									{format(new Date(episode.created_at), "HH:mm")}
								</p>
							</div>
						</section>
					</div>
				</ScrollArea>

				<Separator />

				<div className="px-6 py-3 flex items-center justify-end gap-2 bg-card/30">
					<Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
						Close
					</Button>
					<Button
						variant="outline"
						size="sm"
						onClick={() => setConfirmOpen(true)}
						disabled={deleteEpisode.isPending}
						className="text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
					>
						{deleteEpisode.isPending ? (
							<Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
						) : (
							<Trash2 className="h-3.5 w-3.5 mr-1.5" />
						)}
						Delete
					</Button>
				</div>
			</SheetContent>

			<AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>Delete episode?</AlertDialogTitle>
						<AlertDialogDescription>
							This permanently removes the memory unit from Hindsight. This action cannot be undone.
							The deletion is audited.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel disabled={deleteEpisode.isPending}>Cancel</AlertDialogCancel>
						<AlertDialogAction
							onClick={handleDelete}
							disabled={deleteEpisode.isPending}
							className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							{deleteEpisode.isPending ? "Deleting..." : "Delete episode"}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</Sheet>
	);
}
