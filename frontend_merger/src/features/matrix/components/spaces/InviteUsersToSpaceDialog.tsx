"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import { Check, Loader2, Search, UserPlus } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
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

interface UserSearchResult {
	user_id: string;
	display_name?: string;
	avatar_url?: string;
}

interface Props {
	client: MatrixClient;
	roomId: string;
	roomName?: string;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * E5 Space-Invite-Dialog.
 *
 * Nutzt `client.searchUserDirectory({ term })` fuer Live-Suche, laesst User
 * multi-select, und invited dann jeden via `client.invite(roomId, userId)`.
 *
 * Auch fuer normale Rooms nutzbar — der Prop heisst roomId, muss nicht Space sein.
 */
export function InviteUsersToSpaceDialog({ client, roomId, roomName, open, onOpenChange }: Props) {
	const alive = useAlive();
	const [query, setQuery] = useState("");
	const [results, setResults] = useState<UserSearchResult[]>([]);
	const [selected, setSelected] = useState<Set<string>>(new Set());
	const [searching, setSearching] = useState(false);
	const [inviting, setInviting] = useState(false);

	// Debounced search
	useEffect(() => {
		if (!open) return;
		const trimmed = query.trim();
		if (trimmed.length < 2) {
			setResults([]);
			return;
		}
		const timer = setTimeout(async () => {
			setSearching(true);
			try {
				const resp = await client.searchUserDirectory({ term: trimmed });
				if (alive()) setResults(resp.results ?? []);
			} catch {
				if (alive()) setResults([]);
			} finally {
				if (alive()) setSearching(false);
			}
		}, 300);
		return () => clearTimeout(timer);
	}, [query, client, open, alive]);

	const toggleSelect = useCallback((userId: string) => {
		setSelected((prev) => {
			const next = new Set(prev);
			if (next.has(userId)) next.delete(userId);
			else next.add(userId);
			return next;
		});
	}, []);

	const handleInvite = useCallback(async () => {
		if (selected.size === 0) return;
		setInviting(true);
		let success = 0;
		let failed = 0;
		for (const userId of selected) {
			try {
				await client.invite(roomId, userId);
				success++;
			} catch {
				failed++;
			}
		}
		if (failed === 0) {
			toast.success(`${success} Einladung${success > 1 ? "en" : ""} versendet.`);
		} else {
			toast.warning(`${success} versendet, ${failed} fehlgeschlagen.`);
		}
		if (alive()) {
			setSelected(new Set());
			setQuery("");
			setInviting(false);
			onOpenChange(false);
		}
	}, [client, roomId, selected, onOpenChange, alive]);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<UserPlus className="h-5 w-5 text-primary" />
						Personen einladen
					</DialogTitle>
					<DialogDescription>
						Suche nach Matrix-IDs oder Anzeigenamen. Mehrfach-Auswahl moeglich.
						{roomName && ` Einladung fuer ${roomName}.`}
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-3">
					<div className="relative">
						<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
						<Input
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							placeholder="@alice:matrix.local oder Alice"
							className="pl-8 h-9 text-sm"
							autoFocus
						/>
					</div>

					{selected.size > 0 && (
						<div className="flex flex-wrap gap-1 p-2 bg-muted/30 rounded">
							{[...selected].map((userId) => (
								<span
									key={userId}
									className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary"
								>
									{userId}
								</span>
							))}
						</div>
					)}

					<div className="max-h-64 overflow-y-auto flex flex-col gap-1">
						{searching && (
							<div className="flex items-center justify-center py-4 text-sm text-muted-foreground">
								<Loader2 className="h-4 w-4 animate-spin mr-2" />
								Suche läuft…
							</div>
						)}
						{!searching &&
							results.map((user) => {
								const isSelected = selected.has(user.user_id);
								const initials = (user.display_name ?? user.user_id).slice(0, 2).toUpperCase();
								return (
									<button
										key={user.user_id}
										type="button"
										onClick={() => toggleSelect(user.user_id)}
										className={cn(
											"flex items-center gap-2 p-2 rounded text-left transition-colors",
											isSelected ? "bg-primary/10" : "hover:bg-muted/50",
										)}
									>
										<Avatar className="h-7 w-7 shrink-0">
											{user.avatar_url && (
												<AvatarImage
													src={user.avatar_url}
													alt={user.display_name ?? user.user_id}
												/>
											)}
											<AvatarFallback className="text-[10px] bg-muted text-muted-foreground">
												{initials}
											</AvatarFallback>
										</Avatar>
										<div className="flex-1 min-w-0">
											<div className="text-sm font-medium truncate">
												{user.display_name ?? user.user_id}
											</div>
											<div className="text-[10px] text-muted-foreground truncate">
												{user.user_id}
											</div>
										</div>
										{isSelected && <Check className="h-4 w-4 text-primary shrink-0" />}
									</button>
								);
							})}
						{!searching && query.trim().length >= 2 && results.length === 0 && (
							<p className="text-xs text-muted-foreground text-center py-4">
								Keine Personen gefunden.
							</p>
						)}
						{!searching && query.trim().length < 2 && (
							<p className="text-xs text-muted-foreground text-center py-4">
								Tippe mindestens 2 Zeichen.
							</p>
						)}
					</div>
				</div>

				<DialogFooter>
					<Button variant="outline" onClick={() => onOpenChange(false)} disabled={inviting}>
						Abbrechen
					</Button>
					<Button onClick={() => void handleInvite()} disabled={selected.size === 0 || inviting}>
						{inviting ? (
							<>
								<Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
								Einlade…
							</>
						) : (
							<>
								<UserPlus className="h-3.5 w-3.5 mr-1.5" />
								{selected.size > 0 ? `${selected.size} einladen` : "Einladen"}
							</>
						)}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
