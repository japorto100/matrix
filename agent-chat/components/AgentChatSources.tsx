"use client";

// AC57: Sources panel — displays web citations attached to an assistant message.
// Sources arrive as native ai SDK v6 UIMessage parts:
//   - type: "source-url"  → { sourceId, url, title? }
//   - type: "source-document" → { sourceId, mediaType, data, filename? }
// AC58: Inline count badge + "View N more" Dialog when sources.length > INLINE_LIMIT.

import type { SourceDocumentUIPart, SourceUrlUIPart, UIMessage } from "ai";
import { ExternalLink, Globe } from "lucide-react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

export interface SourceItem {
	title: string;
	url: string;
	snippet?: string;
	favicon?: string;
}

const INLINE_LIMIT = 3;

/** Extract SourceItem[] from a UIMessage via source-url and source-document parts. */
export function extractSources(message: UIMessage): SourceItem[] {
	const sources: SourceItem[] = [];
	for (const part of message.parts) {
		if (part.type === "source-url") {
			const p = part as SourceUrlUIPart;
			sources.push({ title: p.title ?? "", url: p.url });
		} else if (part.type === "source-document") {
			const p = part as SourceDocumentUIPart;
			// source-document has no url — use sourceId as identifier
			sources.push({ title: p.filename ?? p.sourceId, url: "" });
		}
	}
	return sources;
}

function SourceCard({ source }: { source: SourceItem }) {
	let hostname = "";
	try {
		hostname = source.url ? new URL(source.url).hostname.replace(/^www\./, "") : "";
	} catch {
		hostname = source.url;
	}

	const inner = (
		<div className="flex flex-col gap-0.5">
			<div className="flex items-center gap-1.5 min-w-0">
				{source.favicon ? (
					<>
						{/* biome-ignore lint/performance/noImgElement: external favicon from arbitrary domains cannot be whitelisted in next.config.ts; 12x12px has no optimization benefit */}
						<img src={source.favicon} alt="" className="h-3 w-3 shrink-0 rounded-sm" />
					</>
				) : (
					<Globe className="h-3 w-3 shrink-0 text-muted-foreground/60" />
				)}
				<span className="truncate text-[10px] font-medium text-foreground group-hover:text-primary transition-colors">
					{source.title || hostname || source.url}
				</span>
				{source.url && (
					<ExternalLink className="ml-auto h-2.5 w-2.5 shrink-0 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
				)}
			</div>
			{source.snippet && (
				<p className="line-clamp-2 text-[9px] text-muted-foreground/70 leading-relaxed">
					{source.snippet}
				</p>
			)}
			{hostname && <span className="text-[8px] text-muted-foreground/40 truncate">{hostname}</span>}
		</div>
	);

	if (!source.url) {
		return <div className="rounded border border-border/50 bg-muted/30 px-2.5 py-2">{inner}</div>;
	}

	return (
		<a
			href={source.url}
			target="_blank"
			rel="noopener noreferrer"
			className="group rounded border border-border/50 bg-muted/30 px-2.5 py-2 text-left hover:bg-muted/60 hover:border-border transition-colors block"
		>
			{inner}
		</a>
	);
}

interface AgentChatSourcesProps {
	sources: SourceItem[];
}

export function AgentChatSources({ sources }: AgentChatSourcesProps) {
	if (sources.length === 0) return null;

	const inline = sources.slice(0, INLINE_LIMIT);
	const overflow = sources.length - INLINE_LIMIT;

	return (
		<div className="mt-2 space-y-1.5">
			{/* AC58: section header with count badge */}
			<div className="flex items-center gap-1.5">
				<Globe className="h-3 w-3 text-muted-foreground/50" />
				<span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground/50">
					Sources
				</span>
				<span className="rounded bg-muted px-1 py-0.5 text-[8px] font-bold tabular-nums text-muted-foreground/60">
					{sources.length}
				</span>
			</div>

			{/* Inline cards */}
			<div className="grid grid-cols-1 gap-1">
				{inline.map((src, i) => (
					<SourceCard key={`${src.url}-${i}`} source={src} />
				))}
			</div>

			{/* "View N more" overflow dialog */}
			{overflow > 0 && (
				<Dialog>
					<DialogTrigger asChild>
						<button
							type="button"
							className="text-[10px] text-primary/70 hover:text-primary transition-colors underline-offset-2 hover:underline"
						>
							View {overflow} more source{overflow > 1 ? "s" : ""}
						</button>
					</DialogTrigger>
					<DialogContent className="max-w-lg max-h-[70vh] overflow-y-auto">
						<DialogHeader>
							<DialogTitle className="text-sm">
								All sources
								<span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">
									{sources.length}
								</span>
							</DialogTitle>
						</DialogHeader>
						<div className="grid grid-cols-1 gap-1.5 mt-2">
							{sources.map((src, i) => (
								<SourceCard key={`${src.url}-${i}`} source={src} />
							))}
						</div>
					</DialogContent>
				</Dialog>
			)}
		</div>
	);
}
