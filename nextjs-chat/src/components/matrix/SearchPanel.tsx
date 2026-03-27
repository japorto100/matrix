"use client";

import { Loader2, Search, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";

interface Props {
	client: MatrixClient;
	roomId: string;
	onClose: () => void;
}

interface SearchResult {
	eventId: string;
	sender: string;
	body: string;
	timestamp: number;
}

export function SearchPanel({ client, roomId, onClose }: Props) {
	const [query, setQuery] = useState("");
	const [results, setResults] = useState<SearchResult[]>([]);
	const [isSearching, setIsSearching] = useState(false);
	const [hasSearched, setHasSearched] = useState(false);

	const doSearch = useCallback(async () => {
		const trimmed = query.trim();
		if (!trimmed) return;

		setIsSearching(true);
		setHasSearched(true);
		try {
			const response = await client.searchRoomEvents({
				filter: { rooms: [roomId] },
				term: trimmed,
			});
			// biome-ignore lint/suspicious/noExplicitAny: ISearchResults Struktur ist komplex
			const mapped: SearchResult[] = ((response as any).results ?? []).map((r: any) => {
				const ev = r.result ?? r.context?.ourEvent ?? r;
				const content = ev?.getContent?.() ?? ev?.content ?? {};
				return {
					eventId: ev?.getId?.() ?? ev?.event_id ?? "",
					sender: (ev?.getSender?.() ?? ev?.sender ?? "").split(":")[0]?.replace("@", "") ?? "",
					body: (content.body as string) ?? "",
					timestamp: ev?.getTs?.() ?? ev?.origin_server_ts ?? 0,
				};
			});
			setResults(mapped);
		} catch (err) {
			console.error("[SearchPanel] search failed:", err);
			setResults([]);
		} finally {
			setIsSearching(false);
		}
	}, [client, roomId, query]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Enter") doSearch();
		},
		[doSearch],
	);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border/50 bg-background overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
				<span className="text-sm font-semibold">Suche</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			{/* Suchfeld */}
			<div className="px-4 py-3 border-b border-border/50 shrink-0">
				<div className="flex gap-2">
					<div className="flex-1 relative">
						<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
						<input
							type="text"
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							onKeyDown={handleKeyDown}
							placeholder="Nachrichten durchsuchen…"
							className="w-full rounded-lg border border-border/50 bg-muted/30 pl-8 pr-3 py-1.5 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
						/>
					</div>
					<Button size="sm" onClick={doSearch} disabled={isSearching || !query.trim()}>
						{isSearching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Suchen"}
					</Button>
				</div>
			</div>

			{/* Ergebnisse */}
			<div className="flex-1 overflow-y-auto">
				{isSearching && (
					<div className="flex items-center justify-center py-8">
						<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
					</div>
				)}

				{!isSearching && hasSearched && results.length === 0 && (
					<div className="flex items-center justify-center py-8">
						<p className="text-sm text-muted-foreground">Keine Ergebnisse gefunden.</p>
					</div>
				)}

				{!isSearching &&
					results.map((result) => (
						<div
							key={result.eventId}
							className="px-4 py-3 border-b hover:bg-muted/50 transition-colors cursor-pointer"
						>
							<div className="flex items-baseline gap-2 mb-0.5">
								<span className="text-xs font-medium">{result.sender}</span>
								<span className="text-[10px] text-muted-foreground">
									{result.timestamp > 0
										? new Date(result.timestamp).toLocaleString("de-DE", {
												day: "2-digit",
												month: "2-digit",
												year: "2-digit",
												hour: "2-digit",
												minute: "2-digit",
											})
										: ""}
								</span>
							</div>
							<p className="text-sm text-muted-foreground line-clamp-2">{result.body}</p>
						</div>
					))}

				{!isSearching && !hasSearched && (
					<div className="flex items-center justify-center py-8">
						<p className="text-sm text-muted-foreground">Suchbegriff eingeben und Enter drücken.</p>
					</div>
				)}
			</div>
		</div>
	);
}
