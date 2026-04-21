"use client";

import { mxcToHttp } from "@matrix/lib/utils";
import { Loader2, Search, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import type { ISearchResponse, ISearchResult } from "matrix-js-sdk/lib/@types/search";
import { useCallback, useMemo, useRef, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface Props {
	client: MatrixClient;
	roomId: string;
	onClose: () => void;
}

interface RoomSearchResult {
	eventId: string;
	sender: string;
	body: string;
	timestamp: number;
}

interface CrossRoomSearchResult extends RoomSearchResult {
	roomId: string;
	roomName: string;
	roomAvatarUrl?: string;
}

function shortSender(senderRaw: string): string {
	return (senderRaw || "").split(":")[0]?.replace("@", "") ?? "";
}

export function SearchPanel({ client, roomId, onClose }: Props) {
	const [query, setQuery] = useState("");
	const [crossRoom, setCrossRoom] = useState(false);
	const [results, setResults] = useState<RoomSearchResult[]>([]);
	const [crossResults, setCrossResults] = useState<CrossRoomSearchResult[]>([]);
	const [isSearching, setIsSearching] = useState(false);
	const [hasSearched, setHasSearched] = useState(false);
	const [nextBatch, setNextBatch] = useState<string | null>(null);
	const [encryptedSkipped, setEncryptedSkipped] = useState(0);
	const [roomsSearched, setRoomsSearched] = useState(0);
	// Invalidiert in-flight Requests beim Toggle-Flip oder neuem Suchlauf (Verify-Fix).
	const requestIdRef = useRef(0);

	const { searchableRoomIds, encryptedCount, allEncrypted } = useMemo(() => {
		const rooms = client.getRooms().filter((r) => {
			const m = r.getMyMembership();
			return m === "join";
		});
		const encryptedIds = new Set<string>();
		const plainIds: string[] = [];
		for (const r of rooms) {
			if (client.isRoomEncrypted(r.roomId)) encryptedIds.add(r.roomId);
			else plainIds.push(r.roomId);
		}
		return {
			searchableRoomIds: plainIds,
			encryptedCount: encryptedIds.size,
			allEncrypted: rooms.length > 0 && plainIds.length === 0,
		};
	}, [client]);

	const crossRoomDisabled = allEncrypted;

	const mapCrossResult = useCallback(
		(r: ISearchResult): CrossRoomSearchResult => {
			const ev = r.result;
			const rId = ev.room_id;
			const room = client.getRoom(rId);
			const content = (ev.content ?? {}) as { body?: string };
			const mxcAvatar = room?.getMxcAvatarUrl() ?? undefined;
			return {
				eventId: ev.event_id ?? "",
				roomId: rId,
				roomName: room?.name ?? rId,
				roomAvatarUrl: mxcAvatar ? mxcToHttp(mxcAvatar) : undefined,
				sender: shortSender(ev.sender ?? ""),
				body: content.body ?? "",
				timestamp: ev.origin_server_ts ?? 0,
			};
		},
		[client],
	);

	const doSearch = useCallback(
		async (reset = true) => {
			const trimmed = query.trim();
			if (!trimmed) return;

			requestIdRef.current += 1;
			const myRequestId = requestIdRef.current;

			setIsSearching(true);
			setHasSearched(true);
			if (reset) {
				setResults([]);
				setCrossResults([]);
				setNextBatch(null);
			}

			try {
				if (crossRoom) {
					const body = {
						search_categories: {
							room_events: {
								search_term: trimmed,
								order_by: "recent",
								filter: {
									rooms: searchableRoomIds,
								},
								event_context: {
									before_limit: 0,
									after_limit: 0,
									include_profile: true,
								},
							},
						},
					} as unknown as Parameters<MatrixClient["search"]>[0]["body"];

					const batch = !reset && nextBatch ? nextBatch : undefined;
					const response: ISearchResponse = await client.search({
						body,
						next_batch: batch,
					});
					if (myRequestId !== requestIdRef.current) return;
					const cat = response.search_categories?.room_events;
					const rawResults = cat?.results ?? [];
					const mapped = rawResults.map(mapCrossResult);
					setCrossResults((prev) => (reset ? mapped : [...prev, ...mapped]));
					setNextBatch(cat?.next_batch ?? null);
					setEncryptedSkipped(encryptedCount);
					setRoomsSearched(searchableRoomIds.length);
				} else {
					const response = await client.searchRoomEvents({
						filter: { rooms: [roomId] },
						term: trimmed,
					});
					if (myRequestId !== requestIdRef.current) return;
					const mapped: RoomSearchResult[] = (response.results ?? []).map((r) => {
						const ev = r.context.ourEvent;
						const content = ev.getContent();
						return {
							eventId: ev.getId() ?? "",
							sender: shortSender(ev.getSender() ?? ""),
							body: (content.body as string) ?? "",
							timestamp: ev.getTs(),
						};
					});
					setResults(mapped);
				}
			} catch (err) {
				if (myRequestId !== requestIdRef.current) return;
				console.error("[SearchPanel] search failed:", err);
				if (reset) {
					setResults([]);
					setCrossResults([]);
				}
			} finally {
				if (myRequestId === requestIdRef.current) setIsSearching(false);
			}
		},
		[
			client,
			roomId,
			query,
			crossRoom,
			searchableRoomIds,
			encryptedCount,
			nextBatch,
			mapCrossResult,
		],
	);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Enter") void doSearch(true);
		},
		[doSearch],
	);

	const handleResultClick = useCallback((rId: string, eventId: string) => {
		window.dispatchEvent(
			new CustomEvent("matrix:navigate", {
				detail: { type: "room", id: rId, eventId },
			}),
		);
	}, []);

	const showingResults = crossRoom ? crossResults : results;

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border/50 bg-background overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
				<span className="text-sm font-semibold">Suche</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			{/* Suchfeld + Cross-Room-Toggle */}
			<div className="px-4 py-3 border-b border-border/50 shrink-0 space-y-2">
				<div className="flex gap-2">
					<div className="flex-1 relative">
						<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
						<Input
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							onKeyDown={handleKeyDown}
							placeholder="Nachrichten durchsuchen…"
							className="pl-8"
						/>
					</div>
					<Button
						size="sm"
						onClick={() => void doSearch(true)}
						disabled={isSearching || !query.trim()}
					>
						{isSearching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Suchen"}
					</Button>
				</div>

				<div className="flex items-center justify-between gap-2 pt-1">
					{crossRoomDisabled ? (
						<Tooltip>
							<TooltipTrigger asChild>
								<div className="flex items-center gap-2 opacity-50 cursor-not-allowed">
									<Switch id="cross-room" checked={false} disabled />
									<Label
										htmlFor="cross-room"
										className="text-xs text-muted-foreground cursor-not-allowed"
									>
										Alle Räume durchsuchen
									</Label>
								</div>
							</TooltipTrigger>
							<TooltipContent>
								Alle deine Räume sind verschlüsselt — Cross-Room-Suche nicht verfügbar.
							</TooltipContent>
						</Tooltip>
					) : (
						<div className="flex items-center gap-2">
							<Switch
								id="cross-room"
								checked={crossRoom}
								onCheckedChange={(v) => {
									requestIdRef.current += 1;
									setIsSearching(false);
									setCrossRoom(v);
									setHasSearched(false);
									setResults([]);
									setCrossResults([]);
									setNextBatch(null);
								}}
							/>
							<Label htmlFor="cross-room" className="text-xs cursor-pointer">
								Alle Räume durchsuchen
							</Label>
						</div>
					)}
				</div>

				{crossRoom && (
					<p className="text-[10px] text-muted-foreground leading-snug">
						Verschlüsselte Räume werden nicht durchsucht (Matrix-Protokoll-Limitation).
					</p>
				)}
			</div>

			{/* Ergebnisse */}
			<div className="flex-1 overflow-y-auto">
				{isSearching && showingResults.length === 0 && (
					<div className="flex items-center justify-center py-8">
						<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
					</div>
				)}

				{!isSearching && hasSearched && showingResults.length === 0 && (
					<div className="flex flex-col items-center justify-center py-8 px-4 gap-1">
						<p className="text-sm text-muted-foreground">Keine Ergebnisse gefunden.</p>
						{crossRoom && encryptedSkipped > 0 && (
							<p className="text-[10px] text-muted-foreground text-center">
								{roomsSearched} Räume durchsucht · {encryptedSkipped}{" "}
								{encryptedSkipped === 1 ? "verschlüsselter Raum" : "verschlüsselte Räume"}{" "}
								übersprungen.
							</p>
						)}
					</div>
				)}

				{!isSearching &&
					!crossRoom &&
					results.map((result) => (
						<button
							key={result.eventId}
							type="button"
							className="w-full text-left px-4 py-3 border-b hover:bg-muted/50 transition-colors"
							onClick={() => handleResultClick(roomId, result.eventId)}
						>
							<div className="flex items-baseline gap-2 mb-0.5">
								<span className="text-xs font-medium">{result.sender}</span>
								<span className="text-[10px] text-muted-foreground">
									{formatTs(result.timestamp)}
								</span>
							</div>
							<p className="text-sm text-muted-foreground line-clamp-2">{result.body}</p>
						</button>
					))}

				{!isSearching &&
					crossRoom &&
					crossResults.map((result) => (
						<button
							key={`${result.roomId}:${result.eventId}`}
							type="button"
							className="w-full text-left px-4 py-3 border-b hover:bg-muted/50 transition-colors"
							onClick={() => handleResultClick(result.roomId, result.eventId)}
						>
							<div className="flex items-center gap-2 mb-1">
								<Avatar className="h-5 w-5 shrink-0">
									{result.roomAvatarUrl && (
										<AvatarImage src={result.roomAvatarUrl} alt={result.roomName} />
									)}
									<AvatarFallback className="text-[9px] bg-muted">
										{result.roomName.slice(0, 2).toUpperCase()}
									</AvatarFallback>
								</Avatar>
								<span className="text-xs font-semibold truncate flex-1">{result.roomName}</span>
								<span className="text-[10px] text-muted-foreground shrink-0">
									{formatTs(result.timestamp)}
								</span>
							</div>
							<div className="ml-7">
								<span className="text-[10px] text-muted-foreground">{result.sender}: </span>
								<span className="text-sm text-muted-foreground line-clamp-2 inline">
									{result.body}
								</span>
							</div>
						</button>
					))}

				{!isSearching && crossRoom && crossResults.length > 0 && (
					<div className="px-4 py-3 flex flex-col gap-2 items-center">
						{nextBatch && (
							<Button
								variant="outline"
								size="sm"
								onClick={() => void doSearch(false)}
								disabled={isSearching}
								className="w-full"
							>
								{isSearching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Mehr laden"}
							</Button>
						)}
						<p className="text-[10px] text-muted-foreground text-center">
							{roomsSearched} Räume durchsucht
							{encryptedSkipped > 0 &&
								` · ${encryptedSkipped} ${
									encryptedSkipped === 1 ? "verschlüsselter Raum" : "verschlüsselte Räume"
								} übersprungen`}
						</p>
					</div>
				)}

				{!isSearching && !hasSearched && (
					<div className="flex items-center justify-center py-8 px-4 text-center">
						<p className="text-sm text-muted-foreground">
							{crossRoom
								? "Suchbegriff eingeben und alle Räume durchsuchen."
								: "Suchbegriff eingeben und Enter drücken."}
						</p>
					</div>
				)}
			</div>
		</div>
	);
}

function formatTs(ts: number): string {
	if (ts <= 0) return "";
	return new Date(ts).toLocaleString("de-DE", {
		day: "2-digit",
		month: "2-digit",
		year: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
	});
}
