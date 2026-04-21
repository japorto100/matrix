"use client";

// MemoryTimelineView — K2 Slice 3
// Vertical timeline of episodes grouped by day, ordered DESC.
// Reuses `useEpisodes` (already wired via BFF) with mock fallback.

import { format, isToday, isYesterday, parseISO } from "date-fns";
import { Brain, Clock, Wrench } from "lucide-react";
import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { useEpisodes } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { getRoleColor, getRoleLabel, mockEpisodes } from "../mock-data";
import type { Episode } from "../types";

interface DayGroup {
	key: string;
	label: string;
	episodes: Episode[];
}

function formatDayLabel(iso: string): string {
	const d = parseISO(iso);
	if (isToday(d)) return "Today";
	if (isYesterday(d)) return "Yesterday";
	return format(d, "EEEE, MMMM d");
}

function groupByDay(episodes: Episode[]): DayGroup[] {
	const groups = new Map<string, DayGroup>();
	for (const ep of episodes) {
		const day = ep.created_at.slice(0, 10); // YYYY-MM-DD
		const existing = groups.get(day);
		if (existing) {
			existing.episodes.push(ep);
		} else {
			groups.set(day, {
				key: day,
				label: formatDayLabel(ep.created_at),
				episodes: [ep],
			});
		}
	}
	return Array.from(groups.values()).sort((a, b) => b.key.localeCompare(a.key));
}

export function MemoryTimelineView() {
	const query = useEpisodes({ limit: 200 });
	const episodes = (query.data?.items as Episode[] | undefined) ?? mockEpisodes;
	const groups = useMemo(() => groupByDay(episodes), [episodes]);

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Timeline</h2>
					<p className="text-xs text-muted-foreground">
						{episodes.length} episode{episodes.length === 1 ? "" : "s"} across {groups.length} day
						{groups.length === 1 ? "" : "s"}
						{query.isError && (
							<span className="ml-2 text-amber-400">· backend offline (mock data)</span>
						)}
					</p>
				</div>
			</header>

			{groups.length === 0 && (
				<div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
					<Clock className="h-5 w-5" />
					<p className="text-sm">No episodes yet</p>
				</div>
			)}

			<div className="space-y-6">
				{groups.map((group) => (
					<section key={group.key}>
						<div className="flex items-baseline justify-between mb-3 sticky top-0 bg-background/95 backdrop-blur py-1 z-10">
							<h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
								{group.label}
							</h3>
							<Badge variant="outline" className="text-[10px]">
								{group.episodes.length}
							</Badge>
						</div>

						<div className="relative pl-6 space-y-3 border-l border-border/60 ml-1.5">
							{group.episodes.map((ep) => {
								const color = getRoleColor(ep.agent_role);
								const label = getRoleLabel(ep.agent_role);
								const time = format(parseISO(ep.created_at), "HH:mm");

								return (
									<div key={ep.id} className="relative">
										{/* Timeline dot */}
										<div
											className={cn(
												"absolute -left-[26px] top-2 h-2.5 w-2.5 rounded-full border-2 border-background",
												color.replace("text-", "bg-"),
											)}
										/>

										<div className="rounded-lg border border-border bg-card/40 p-3 hover:border-accent transition-colors cursor-pointer">
											<div className="flex items-center justify-between gap-2 mb-1.5">
												<div className="flex items-center gap-2 min-w-0">
													<Brain className={cn("h-3 w-3 shrink-0", color)} />
													<span className="text-xs font-medium truncate">{label}</span>
													{ep.session_id && (
														<code className="text-[9px] text-muted-foreground font-mono truncate">
															{ep.session_id}
														</code>
													)}
												</div>
												<span className="text-[10px] font-mono text-muted-foreground shrink-0">
													{time}
												</span>
											</div>
											{ep.input && (
												<p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
													{ep.input}
												</p>
											)}
											<div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground">
												<div className="flex items-center gap-1">
													<Wrench className="h-2.5 w-2.5" />
													{ep.tools_used.length} tools
												</div>
												{ep.duration_ms && <span>·</span>}
												{ep.duration_ms && (
													<span className="font-mono">
														{ep.duration_ms < 1000
															? `${ep.duration_ms}ms`
															: `${(ep.duration_ms / 1000).toFixed(1)}s`}
													</span>
												)}
												{ep.tags?.length > 0 && (
													<>
														<span>·</span>
														<div className="flex gap-1">
															{ep.tags.slice(0, 3).map((tag) => (
																<Badge
																	key={tag}
																	variant="secondary"
																	className="text-[9px] h-4 px-1.5"
																>
																	{tag}
																</Badge>
															))}
														</div>
													</>
												)}
											</div>
										</div>
									</div>
								);
							})}
						</div>
					</section>
				))}
			</div>
		</div>
	);
}
