"use client";

import { Lock, LockOpen, ShieldBan, Trash2, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
	client: MatrixClient;
	roomId: string;
	otherUserId: string;
	onClose: () => void;
}

export function DMInfoPanel({ client, roomId, otherUserId, onClose }: Props) {
	const [isLeaving, setIsLeaving] = useState(false);
	const [leaveConfirm, setLeaveConfirm] = useState(false);
	const [isBlocked, setIsBlocked] = useState(false);

	const room = client.getRoom(roomId);
	const isEncrypted = !!room?.currentState.getStateEvents("m.room.encryption", "");

	// Anderen User laden
	const otherUser = client.getUser(otherUserId);
	const otherMember = room?.getMember(otherUserId);
	const displayName = otherMember?.name ?? otherUser?.displayName ?? otherUserId;
	const initials = displayName.slice(0, 2).toUpperCase() || "?";
	const mxcAvatar = otherMember?.getMxcAvatarUrl() ?? otherUser?.avatarUrl;
	const avatarSrc = mxcAvatar?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(mxcAvatar.slice(6))}`
		: undefined;

	// Block-Status prüfen
	useEffect(() => {
		const ignored = client.getIgnoredUsers?.() ?? [];
		setIsBlocked(ignored.includes(otherUserId));
	}, [client, otherUserId]);

	const toggleBlock = useCallback(async () => {
		try {
			const token = client.getAccessToken();
			const base = client.baseUrl;
			const uid = encodeURIComponent(client.getUserId() ?? "");
			const res = await fetch(
				`${base}/_matrix/client/v3/user/${uid}/account_data/m.ignored_user_list`,
				{
					headers: { Authorization: `Bearer ${token}` },
				},
			);
			const current = res.ok ? await res.json() : { ignored_users: {} };
			const ignoredUsers = current.ignored_users ?? {};
			if (isBlocked) {
				delete ignoredUsers[otherUserId];
			} else {
				ignoredUsers[otherUserId] = {};
			}
			await fetch(`${base}/_matrix/client/v3/user/${uid}/account_data/m.ignored_user_list`, {
				method: "PUT",
				headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
				body: JSON.stringify({ ignored_users: ignoredUsers }),
			});
			setIsBlocked(!isBlocked);
			toast.success(isBlocked ? "Benutzer entblockt." : "Benutzer blockiert.");
		} catch {
			toast.error("Blockieren fehlgeschlagen.");
		}
	}, [client, otherUserId, isBlocked]);

	const deleteChat = useCallback(async () => {
		setIsLeaving(true);
		try {
			const matrixRoom = client.getRoom(roomId);
			const membership = matrixRoom?.getMyMembership();
			if (membership === "join") {
				const token = client.getAccessToken();
				const base = client.baseUrl;
				const rid = encodeURIComponent(roomId);
				await fetch(`${base}/_matrix/client/v3/rooms/${rid}/leave`, {
					method: "POST",
					headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
					body: "{}",
				});
				await fetch(`${base}/_matrix/client/v3/rooms/${rid}/forget`, {
					method: "POST",
					headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
					body: "{}",
				}).catch(() => {});
			}
			client.store.removeRoom(roomId);
			client.emit("deleteRoom" as any, roomId);
			onClose();
		} catch {
			toast.error("Chat konnte nicht gelöscht werden.");
		} finally {
			setIsLeaving(false);
		}
	}, [client, roomId, onClose]);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border bg-background overflow-hidden">
			<div className="flex items-center justify-between h-[57px] px-4 border-b border-border bg-background shrink-0">
				<span className="text-sm font-semibold">Info</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<div className="flex-1 overflow-y-auto p-4 space-y-5">
				{/* Avatar + Name */}
				<div className="flex flex-col items-center text-center gap-2">
					<Avatar className="h-[72px] w-[72px]">
						{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
						<AvatarFallback className="text-lg font-semibold bg-muted">{initials}</AvatarFallback>
					</Avatar>
					<div>
						<p className="font-semibold text-base">{displayName}</p>
						<p className="text-xs text-muted-foreground">{otherUserId}</p>
					</div>
					<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
						{isEncrypted ? (
							<>
								<Lock className="h-3.5 w-3.5 text-emerald-500" />
								<span>Verschlüsselt</span>
							</>
						) : (
							<>
								<LockOpen className="h-3.5 w-3.5 text-destructive/70" />
								<span>Nicht verschlüsselt</span>
							</>
						)}
					</div>
				</div>

				{/* Block */}
				<button
					type="button"
					onClick={toggleBlock}
					className={cn(
						"w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
						isBlocked
							? "bg-destructive/10 text-destructive hover:bg-destructive/20"
							: "hover:bg-muted/50 text-muted-foreground hover:text-foreground",
					)}
				>
					<ShieldBan className="h-4 w-4" />
					{isBlocked ? "Benutzer entblocken" : "Benutzer blockieren"}
				</button>
			</div>

			{/* Footer */}
			<div className="p-3 border-t border-border shrink-0">
				{leaveConfirm ? (
					<div className="flex items-center gap-2">
						<span className="text-xs text-muted-foreground flex-1">Chat wirklich löschen?</span>
						<Button size="sm" variant="ghost" onClick={() => setLeaveConfirm(false)}>
							Abbrechen
						</Button>
						<Button size="sm" variant="destructive" onClick={deleteChat} disabled={isLeaving}>
							{isLeaving ? "…" : "Bestätigen"}
						</Button>
					</div>
				) : (
					<Button
						variant="outline"
						className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive"
						onClick={() => setLeaveConfirm(true)}
					>
						<Trash2 className="h-4 w-4 mr-2" />
						Chat löschen
					</Button>
				)}
			</div>
		</div>
	);
}
