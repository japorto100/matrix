"use client";

import {
	Bell,
	BellOff,
	Check,
	Clock,
	FileText,
	Image,
	Link2,
	Lock,
	LockOpen,
	ShieldBan,
	Trash2,
	X,
} from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
	client: MatrixClient;
	roomId: string;
	dmUserId: string;
	membership: "join" | "invite" | "leave";
	onClose: () => void;
}

export function DMInfoPanel({ client, roomId, dmUserId, membership, onClose }: Props) {
	const [isLeaving, setIsLeaving] = useState(false);
	const [leaveConfirm, setLeaveConfirm] = useState(false);
	const [isBlocked, setIsBlocked] = useState(false);
	const [isMuted, setIsMuted] = useState(false);

	const room = client.getRoom(roomId);
	const isEncrypted = !!room?.currentState.getStateEvents("m.room.encryption", "");

	// SDK: User-Daten
	const otherUser = client.getUser(dmUserId);
	const otherMember = room?.getMember(dmUserId);

	// Display-Name: Member → User → ID-Fallback
	const displayName =
		(otherMember?.name && otherMember.name !== dmUserId ? otherMember.name : null) ??
		otherUser?.displayName ??
		dmUserId.split(":")[0]?.replace("@", "") ??
		dmUserId;
	const initials = displayName.slice(0, 2).toUpperCase() || "?";

	// Avatar
	const mxcAvatar = otherMember?.getMxcAvatarUrl() ?? otherUser?.avatarUrl;
	const avatarSrc = mxcAvatar?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(mxcAvatar.slice(6))}`
		: undefined;

	// SDK: Presence
	const isOnline = otherUser?.currentlyActive ?? false;
	const presence = otherUser?.presence ?? "offline";
	const lastActiveAgo = otherUser?.lastActiveAgo ?? 0;
	const statusMsg = otherUser?.presenceStatusMsg;

	const presenceText = (() => {
		if (isOnline || presence === "online") return "Online";
		if (lastActiveAgo > 0) {
			const mins = Math.round(lastActiveAgo / 60000);
			if (mins < 60) return `Zuletzt online vor ${mins}m`;
			const hours = Math.round(mins / 60);
			if (hours < 24) return `Zuletzt online vor ${hours}h`;
			return `Zuletzt online vor ${Math.round(hours / 24)}d`;
		}
		if (presence === "unavailable") return "Abwesend";
		return "Offline";
	})();

	// SDK: Block-Status
	useEffect(() => {
		setIsBlocked(client.getIgnoredUsers().includes(dmUserId));
	}, [client, dmUserId]);

	// Mute-Status
	useEffect(() => {
		try {
			// biome-ignore lint/suspicious/noExplicitAny: push_rules nicht typisiert
			const pushRules = (client.getAccountData as any)("m.push_rules")?.getContent();
			const overrides =
				(pushRules?.global as { override?: Array<{ rule_id: string; enabled: boolean }> })
					?.override ?? [];
			setIsMuted(!!overrides.find((r: { rule_id: string }) => r.rule_id === roomId)?.enabled);
		} catch {
			/* ignore */
		}
	}, [client, roomId]);

	// Gemeinsame Räume
	const sharedRooms = (() => {
		const rooms = client.getRooms();
		return rooms
			.filter(
				(r) =>
					r.getMyMembership() === "join" &&
					r.getMember(dmUserId)?.membership === "join" &&
					r.roomId !== roomId,
			)
			.map((r) => r.name ?? r.roomId);
	})();

	// Geteilte Medien (aus Timeline zählen)
	const mediaCounts = (() => {
		if (!room) return { images: 0, files: 0, links: 0 };
		const events = room.getLiveTimeline().getEvents();
		let images = 0;
		let files = 0;
		let links = 0;
		for (const ev of events) {
			if (ev.getType() !== "m.room.message") continue;
			const msgtype = ev.getContent()?.msgtype;
			if (msgtype === "m.image") images++;
			else if (msgtype === "m.file" || msgtype === "m.video" || msgtype === "m.audio") files++;
			if ((ev.getContent()?.body as string)?.match(/https?:\/\//)) links++;
		}
		return { images, files, links };
	})();

	// SDK: Mute toggle
	const toggleMute = useCallback(async () => {
		try {
			if (isMuted) {
				// biome-ignore lint/suspicious/noExplicitAny: PushRuleKind nicht typisiert
				await (client.deletePushRule as any)("global", "override", roomId);
			} else {
				// biome-ignore lint/suspicious/noExplicitAny: PushRuleKind nicht typisiert
				await (client.addPushRule as any)("global", "override", roomId, {
					conditions: [{ kind: "event_match", key: "room_id", pattern: roomId }],
					actions: ["dont_notify"],
				});
			}
			setIsMuted(!isMuted);
		} catch {
			toast.error("Stummschalten fehlgeschlagen.");
		}
	}, [client, roomId, isMuted]);

	// SDK: Block toggle
	const toggleBlock = useCallback(async () => {
		try {
			const ignored = client.getIgnoredUsers();
			if (isBlocked) {
				await client.setIgnoredUsers(ignored.filter((id) => id !== dmUserId));
			} else {
				await client.setIgnoredUsers([...ignored, dmUserId]);
			}
			setIsBlocked(!isBlocked);
			toast.success(isBlocked ? "Benutzer entblockt." : "Benutzer blockiert.");
		} catch {
			toast.error("Blockieren fehlgeschlagen.");
		}
	}, [client, dmUserId, isBlocked]);

	// SDK: Leave + Forget
	const deleteChat = useCallback(async () => {
		setIsLeaving(true);
		try {
			if (room?.getMyMembership() === "join") {
				await client.leave(roomId);
				await client.forget(roomId).catch(() => {});
			}
			onClose();
		} catch {
			toast.error("Chat konnte nicht gelöscht werden.");
		} finally {
			setIsLeaving(false);
		}
	}, [client, roomId, room, onClose]);

	// Invite-Status des anderen Users
	const otherMembership = room?.getMember(dmUserId)?.membership;

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border bg-background overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between h-[57px] px-4 border-b border-border bg-background shrink-0">
				<span className="text-sm font-semibold">Info</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<div className="flex-1 overflow-y-auto p-4 space-y-4">
				{/* Avatar + Name + Presence */}
				<div className="flex flex-col items-center text-center gap-2">
					<div className="relative">
						<Avatar className="h-[72px] w-[72px]">
							{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
							<AvatarFallback className="text-lg font-semibold bg-muted">{initials}</AvatarFallback>
						</Avatar>
						{(isOnline || presence === "online") && (
							<span className="absolute bottom-1 right-1 h-3.5 w-3.5 rounded-full bg-emerald-500 border-2 border-background" />
						)}
					</div>
					<div>
						<p className="font-semibold text-base">{displayName}</p>
						<p className="text-xs text-muted-foreground">{dmUserId}</p>
						<p
							className={cn(
								"text-[10px] mt-0.5",
								isOnline || presence === "online" ? "text-emerald-500" : "text-muted-foreground",
							)}
						>
							{presenceText}
						</p>
						{statusMsg && (
							<p className="text-[10px] text-muted-foreground/70 italic mt-0.5">"{statusMsg}"</p>
						)}
					</div>
					{/* E2EE */}
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

				{/* Invite-Status */}
				{otherMembership === "invite" && (
					<div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 text-amber-500 text-sm">
						<Clock className="h-4 w-4 shrink-0" />
						<span>Einladung ausstehend</span>
					</div>
				)}
				{membership === "invite" && (
					<div className="flex gap-2">
						<Button
							className="flex-1 gap-1"
							onClick={() =>
								client
									.joinRoom(roomId)
									.then(() => toast.success("Angenommen"))
									.catch(() => toast.error("Fehlgeschlagen"))
							}
						>
							<Check className="h-4 w-4" /> Annehmen
						</Button>
						<Button
							variant="outline"
							className="flex-1 gap-1 text-destructive"
							onClick={() => {
								client.leave(roomId).catch(() => {});
								onClose();
							}}
						>
							<X className="h-4 w-4" /> Ablehnen
						</Button>
					</div>
				)}

				{/* Aktionen */}
				{membership === "join" && (
					<div className="space-y-1">
						<button
							type="button"
							onClick={toggleMute}
							className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors"
						>
							{isMuted ? <BellOff className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
							{isMuted ? "Benachrichtigungen aktivieren" : "Stummschalten"}
						</button>
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
				)}

				{/* Geteilte Medien */}
				{(mediaCounts.images > 0 || mediaCounts.files > 0 || mediaCounts.links > 0) && (
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-2 block">
							Geteilte Medien
						</label>
						<div className="flex gap-3">
							{mediaCounts.images > 0 && (
								<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
									<Image className="h-3.5 w-3.5" />
									<span>{mediaCounts.images} Bilder</span>
								</div>
							)}
							{mediaCounts.files > 0 && (
								<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
									<FileText className="h-3.5 w-3.5" />
									<span>{mediaCounts.files} Dateien</span>
								</div>
							)}
							{mediaCounts.links > 0 && (
								<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
									<Link2 className="h-3.5 w-3.5" />
									<span>{mediaCounts.links} Links</span>
								</div>
							)}
						</div>
					</div>
				)}

				{/* Gemeinsame Räume */}
				{sharedRooms.length > 0 && (
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-2 block">
							Gemeinsame Räume ({sharedRooms.length})
						</label>
						<div className="flex flex-col gap-1">
							{sharedRooms.slice(0, 5).map((name) => (
								<p key={name} className="text-xs text-muted-foreground truncate px-1">
									# {name}
								</p>
							))}
							{sharedRooms.length > 5 && (
								<p className="text-[10px] text-muted-foreground px-1">
									+{sharedRooms.length - 5} weitere
								</p>
							)}
						</div>
					</div>
				)}
			</div>

			{/* Footer */}
			<div className="p-3 border-t border-border shrink-0">
				{membership === "invite" ? null : leaveConfirm ? (
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
						<Trash2 className="h-4 w-4 mr-2" /> Chat löschen
					</Button>
				)}
			</div>
		</div>
	);
}
