"use client";

// MemoryPage — Memory surface entry point
// Routes /memory, /memory/timeline, /memory/graph, /memory/kg, /memory/ingestion
// URL is source of truth via usePathname + nuqs.

import { usePathname } from "next/navigation";
import { useQueryState } from "nuqs";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { useEpisodes, useIngestNote } from "@/lib/queries/hooks";
import { episodeParam, rolesParam, viewParam } from "@/lib/search-params";
import { EpisodeCard } from "./components/EpisodeCard";
import { EpisodeDetailSheet } from "./components/EpisodeDetailSheet";
import { EpisodeFilterBar } from "./components/EpisodeFilterBar";
import { EpisodesGrid } from "./components/EpisodesGrid";
import { FullscreenNoteModal } from "./components/FullscreenNoteModal";
import { type HighlightItem, HighlightsCard } from "./components/HighlightsCard";
import { IngestionStatusPage } from "./components/IngestionStatusPage";
import { MemoryHealthCards } from "./components/MemoryHealthCards";
import { MemoryTimelineView } from "./components/MemoryTimelineView";
import { MemoryTopNav } from "./components/MemoryTopNav";
import { QuickNoteCard } from "./components/QuickNoteCard";
import { KGGraphPage } from "./KGGraphPage";
import { KGPage } from "./kg/KGPage";
import { mockEpisodes } from "./mock-data";
import type { Episode } from "./types";

// Mock highlights — replace with real /api/control/memory/highlights in Slice 3.5
const MOCK_HIGHLIGHTS: HighlightItem[] = [
	{
		id: "h1",
		title: "BTC volatility regime shifted",
		content: "Realized vol doubled from 42% to 85% annualized over Mar–Apr.",
		format: "one_liner",
		query: "BTC volatility",
		source_episode_ids: ["ep_001"],
	},
	{
		id: "h2",
		title: "Risk-Off triggers",
		content: "- VIX > 25\n- Bond yields falling\n- Equity outflows persistent",
		format: "bullets",
		query: "risk-off regime",
		source_episode_ids: ["ep_004", "ep_005"],
	},
	{
		id: "h3",
		title: "Position sizing rule",
		content:
			"Never exceed 5% of portfolio per single name unless explicitly approved by risk_manager.",
		format: "quote",
		query: "position sizing risk",
		source_episode_ids: ["ep_004"],
	},
];

function EpisodesView() {
	const [episodeId, setEpisodeId] = useQueryState("episode", episodeParam);
	const [selectedRoles] = useQueryState("roles", rolesParam);
	const [view] = useQueryState("view", viewParam);
	const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null);
	const [fullscreenOpen, setFullscreenOpen] = useState(false);
	const [fullscreenInitial, setFullscreenInitial] = useState("");

	// Slice 7 Phase H: real backend with mock fallback
	const episodesQuery = useEpisodes({ limit: 100 });
	const episodes = (episodesQuery.data?.items as Episode[] | undefined) ?? mockEpisodes;

	// Slice 2 write path: ingest notes via /api/control/ingest/note
	const ingestNote = useIngestNote();

	const filteredEpisodes = useMemo(() => {
		if (selectedRoles.length === 0) return episodes;
		return episodes.filter((ep) => selectedRoles.includes(ep.agent_role));
	}, [episodes, selectedRoles]);

	const roleCounts = useMemo(() => {
		const counts: Record<string, number> = {};
		for (const ep of episodes) {
			counts[ep.agent_role] = (counts[ep.agent_role] ?? 0) + 1;
		}
		return counts;
	}, [episodes]);

	const handleEpisodeClick = useCallback(
		(episode: Episode) => {
			setSelectedEpisode(episode);
			setEpisodeId(episode.id);
		},
		[setEpisodeId],
	);

	const handleSheetOpenChange = useCallback(
		(open: boolean) => {
			if (!open) {
				setSelectedEpisode(null);
				setEpisodeId(null);
			}
		},
		[setEpisodeId],
	);

	const handleQuickNoteSave = useCallback(
		async (content: string) => {
			if (!content.trim()) return;
			try {
				const result = await ingestNote.mutateAsync({
					text: content,
					tags: ["quicknote"],
				});
				toast.success(
					result.status === "ok"
						? `Note saved (${result.chunks ?? 0} chunks)`
						: result.status === "dedup_skip"
							? "Duplicate note — skipped"
							: "Note queued",
				);
			} catch (err) {
				toast.error(`Failed to save note: ${err instanceof Error ? err.message : "unknown"}`);
			}
		},
		[ingestNote],
	);

	const handleQuickNoteMaximize = useCallback((content: string) => {
		setFullscreenInitial(content);
		setFullscreenOpen(true);
	}, []);

	const handleFullscreenSave = useCallback(
		async (content: string) => {
			if (!content.trim()) {
				setFullscreenOpen(false);
				return;
			}
			try {
				const result = await ingestNote.mutateAsync({
					text: content,
					tags: ["fullscreen-note"],
				});
				toast.success(
					result.status === "ok" ? `Note saved (${result.chunks ?? 0} chunks)` : "Note queued",
				);
				setFullscreenOpen(false);
			} catch (err) {
				toast.error(`Failed to save note: ${err instanceof Error ? err.message : "unknown"}`);
			}
		},
		[ingestNote],
	);

	return (
		<div className="flex flex-col">
			<MemoryHealthCards />

			{/* Quick Note + Highlights — top widgets (supermemory pattern) */}
			<section className="grid grid-cols-1 md:grid-cols-2 gap-4 px-6 py-4">
				<QuickNoteCard onSave={handleQuickNoteSave} onMaximize={handleQuickNoteMaximize} />
				<HighlightsCard items={MOCK_HIGHLIGHTS} />
			</section>

			<div className="border-t border-border/30 mt-2 pt-4">
				<EpisodeFilterBar totalCount={episodes.length} roleCounts={roleCounts} />

				{view === "grid" && <EpisodesGrid onEpisodeClick={handleEpisodeClick} />}

				{view === "table" && (
					<div className="px-6 py-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
						{filteredEpisodes.map((ep) => (
							<EpisodeCard key={ep.id} episode={ep} onClick={handleEpisodeClick} />
						))}
					</div>
				)}

				{view === "timeline" && <MemoryTimelineView />}
			</div>

			<EpisodeDetailSheet
				episode={selectedEpisode}
				open={!!selectedEpisode || !!episodeId}
				onOpenChange={handleSheetOpenChange}
			/>

			<FullscreenNoteModal
				isOpen={fullscreenOpen}
				onClose={() => setFullscreenOpen(false)}
				initialContent={fullscreenInitial}
				onSave={handleFullscreenSave}
			/>
		</div>
	);
}

export function MemoryPage() {
	const pathname = usePathname();

	const renderSubtab = () => {
		if (pathname.startsWith("/memory/kg")) {
			return <KGPage />;
		}
		if (pathname.startsWith("/memory/graph")) {
			return <KGGraphPage />;
		}
		if (pathname.startsWith("/memory/ingestion")) {
			return <IngestionStatusPage />;
		}
		// Default /memory and /memory/timeline → Episodes Browser
		return <EpisodesView />;
	};

	return (
		<div className="flex flex-col h-full">
			<MemoryTopNav />
			<div className="flex-1 overflow-auto">{renderSubtab()}</div>
		</div>
	);
}
