"use client";

import { createAsyncSearch } from "@matrix/lib/asyncSearch";
import { useAlive } from "@matrix/lib/hooks/useAlive";
import type { RoomInfo } from "@matrix/lib/types";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Check, Loader2, Plus, Search } from "lucide-react";
import { EventType, type MatrixClient } from "matrix-js-sdk";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { cn } from "@/lib/utils";

interface Props {
	client: MatrixClient;
	spaceId: string;
	spaceName?: string;
	/** bereits Children im Space — werden aus der Auswahl ausgeschlossen. */
	existingChildIds: Set<string>;
	rooms: RoomInfo[];
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onAdded: () => void;
}

const searchRooms = createAsyncSearch<RoomInfo>({
	searchFields: (r) => [r.name, r.roomId],
});

const ROW_HEIGHT = 48;

/**
 * F1 add-existing Room Picker Modal.
 *
 * Virtualisierte Liste aller Rooms die der User joined hat, minus die bereits
 * im Space enthaltenen. Search + Multi-Select. Submit sendet pro gewaehltem
 * Room ein `m.space.child` State-Event im Parent-Space.
 */
export function AddRoomToSpaceDialog({
	client,
	spaceId,
	spaceName,
	existingChildIds,
	rooms,
	open,
	onOpenChange,
	onAdded,
}: Props) {
	const alive = useAlive();
	const [query, setQuery] = useState("");
	const [selected, setSelected] = useState<Set<string>>(new Set());
	const [adding, setAdding] = useState(false);
	const scrollRef = useRef<HTMLDivElement>(null);

	const candidates = useMemo(() => {
		const filtered = rooms.filter(
			(r) => r.roomId !== spaceId && !existingChildIds.has(r.roomId) && r.membership === "join",
		);
		return searchRooms(query, filtered);
	}, [rooms, spaceId, existingChildIds, query]);

	const virtualizer = useVirtualizer({
		count: candidates.length,
		getScrollElement: () => scrollRef.current,
		estimateSize: () => ROW_HEIGHT,
		overscan: 5,
	});

	const toggleSelect = useCallback((roomId: string) => {
		setSelected((prev) => {
			const next = new Set(prev);
			if (next.has(roomId)) next.delete(roomId);
			else next.add(roomId);
			return next;
		});
	}, []);

	const handleAdd = useCallback(async () => {
		if (selected.size === 0) return;
		setAdding(true);
		const via = client.getDomain() ?? "matrix.local";
		let success = 0;
		let failed = 0;
		for (const roomId of selected) {
			try {
				await (
					client.sendStateEvent as (r: string, t: string, c: unknown, s: string) => Promise<unknown>
				)(spaceId, EventType.SpaceChild, { via: [via] }, roomId);
				success++;
			} catch {
				failed++;
			}
		}
		if (failed === 0) {
			toast.success(`${success} Raum${success > 1 ? "e" : ""} hinzugefuegt.`);
		} else {
			toast.warning(`${success} hinzugefuegt, ${failed} fehlgeschlagen.`);
		}
		if (alive()) {
			setSelected(new Set());
			setQuery("");
			setAdding(false);
			onAdded();
			onOpenChange(false);
		}
	}, [client, spaceId, selected, onOpenChange, onAdded, alive]);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Plus className="h-5 w-5 text-primary" />
						Raum zum Space hinzufuegen
					</DialogTitle>
					<DialogDescription>
						Waehle Raeume aus deiner Liste, die {spaceName ? `zu "${spaceName}"` : "diesem Space"}{" "}
						hinzugefuegt werden sollen.
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-3">
					<div className="relative">
						<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
						<Input
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							placeholder="Raum-Name oder ID suchen…"
							className="pl-8 h-9 text-sm"
							autoFocus
						/>
					</div>

					<div ref={scrollRef} className="max-h-64 overflow-y-auto border border-border/40 rounded">
						{candidates.length === 0 ? (
							<p className="text-xs text-muted-foreground text-center py-6">
								{query
									? "Keine Raeume passend zur Suche."
									: "Alle deine Raeume sind bereits im Space."}
							</p>
						) : (
							<div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
								{virtualizer.getVirtualItems().map((vRow) => {
									const room = candidates[vRow.index];
									if (!room) return null;
									const isSelected = selected.has(room.roomId);
									const initials = room.name.slice(0, 2).toUpperCase();
									return (
										<button
											key={room.roomId}
											type="button"
											onClick={() => toggleSelect(room.roomId)}
											style={{
												position: "absolute",
												top: 0,
												left: 0,
												width: "100%",
												height: ROW_HEIGHT,
												transform: `translateY(${vRow.start}px)`,
											}}
											className={cn(
												"flex items-center gap-2 px-2 py-1.5 text-left transition-colors",
												isSelected ? "bg-primary/10" : "hover:bg-muted/30",
											)}
										>
											<Avatar className="h-7 w-7 shrink-0">
												{room.avatarUrl && <AvatarImage src={room.avatarUrl} alt={room.name} />}
												<AvatarFallback className="text-[10px] bg-muted text-muted-foreground">
													{initials}
												</AvatarFallback>
											</Avatar>
											<div className="flex-1 min-w-0">
												<div className="text-sm font-medium truncate">{room.name}</div>
												<div className="text-[10px] text-muted-foreground">
													{room.memberCount} Mitglieder
												</div>
											</div>
											{isSelected && <Check className="h-4 w-4 text-primary shrink-0" />}
										</button>
									);
								})}
							</div>
						)}
					</div>

					{selected.size > 0 && (
						<p className="text-[11px] text-muted-foreground">
							{selected.size} Raum{selected.size > 1 ? "e" : ""} ausgewaehlt.
						</p>
					)}
				</div>

				<DialogFooter>
					<Button variant="outline" onClick={() => onOpenChange(false)} disabled={adding}>
						Abbrechen
					</Button>
					<Button onClick={() => void handleAdd()} disabled={selected.size === 0 || adding}>
						{adding ? (
							<>
								<Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
								Fuege hinzu…
							</>
						) : (
							<>
								<Plus className="h-3.5 w-3.5 mr-1.5" />
								Hinzufuegen
							</>
						)}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
