"use client";

// EpisodesGrid — Masonry layout with infinite loading
// Pattern adapted from _ref/supermemory/apps/web/components/memories-grid.tsx
// Uses `masonic` for performant masonry rendering.

import type { MasonryProps, RenderComponentProps } from "masonic";
import dynamic from "next/dynamic";
import { useCallback } from "react";
import { useEpisodes } from "@/lib/queries/hooks";
import { mockEpisodes } from "../mock-data";
import type { Episode } from "../types";
import { EpisodeCard } from "./EpisodeCard";

// masonic touches ResizeObserver during module initialization in some builds.
// In Next App Router this can break server rendering for pages that import it.
// Load it client-only to avoid `ReferenceError: ResizeObserver is not defined`.
const Masonry = dynamic(() => import("masonic").then((m) => m.Masonry), {
	ssr: false,
}) as unknown as <T>(
	props: MasonryProps<T> & { render: React.ComponentType<RenderComponentProps<T>> },
) => React.ReactElement | null;

interface EpisodesGridProps {
	onEpisodeClick?: (episode: Episode) => void;
}

export function EpisodesGrid({ onEpisodeClick }: EpisodesGridProps) {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useEpisodes({ limit: 100 });
	const episodes = (query.data?.items as Episode[] | undefined) ?? mockEpisodes;

	const renderItem = useCallback(
		({ data }: RenderComponentProps<Episode>) => (
			<EpisodeCard episode={data} onClick={onEpisodeClick} />
		),
		[onEpisodeClick],
	);

	if (episodes.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center py-16 px-6 gap-2 text-muted-foreground">
				<p className="text-sm">No episodes yet</p>
				<p className="text-xs text-muted-foreground/70">Episodes appear here as the agent runs</p>
			</div>
		);
	}

	return (
		<div className="px-6 py-4">
			<Masonry
				key={episodes.length}
				items={episodes}
				render={renderItem as MasonryProps<Episode>["render"]}
				columnGutter={12}
				rowGutter={12}
				columnWidth={280}
				overscanBy={2}
			/>
		</div>
	);
}
