"use client";

import { Bell, BellOff, Lock, LockOpen, Phone, Search, UserPlus, Users, Video } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import type { RoomInfo } from "@/lib/matrix/types";
import { InviteDialog } from "./InviteDialog";

interface Props {
	room: RoomInfo;
	client?: MatrixClient | null;
	roomId?: string;
	onCall?: (withVideo: boolean) => void;
	onSettingsOpen?: () => void;
	onSearchOpen?: () => void;
}

export function RoomHeader({ room, client, roomId, onCall, onSettingsOpen, onSearchOpen }: Props) {
	const [isMuted, setIsMuted] = useState(false);

	// UI-9: Mute-Status prüfen
	useEffect(() => {
		if (!client || !roomId) return;
		try {
			// biome-ignore lint/suspicious/noExplicitAny: push_rules AccountData nicht typisiert
			const pushRules = (client.getAccountData as any)("m.push_rules")?.getContent();
			const overrides =
				(pushRules?.global as { override?: Array<{ rule_id: string; enabled: boolean }> })
					?.override ?? [];
			const muteRule = overrides.find((r: { rule_id: string }) => r.rule_id === roomId);
			setIsMuted(!!muteRule?.enabled);
		} catch (err) {
			console.error("[RoomHeader] push rules check failed:", err);
		}
	}, [client, roomId]);

	// UI-9: Mute/Unmute toggle
	const toggleMute = useCallback(async () => {
		if (!client || !roomId) return;
		try {
			if (isMuted) {
				// biome-ignore lint/suspicious/noExplicitAny: PushRuleKind Type-Mismatch im SDK
				await (client.deletePushRule as any)("global", "override", roomId);
				setIsMuted(false);
			} else {
				// biome-ignore lint/suspicious/noExplicitAny: PushRuleKind Type-Mismatch im SDK
				await (client.addPushRule as any)("global", "override", roomId, {
					conditions: [{ kind: "event_match", key: "room_id", pattern: roomId }],
					actions: ["dont_notify"],
				});
				setIsMuted(true);
			}
		} catch (err) {
			console.error("[RoomHeader] mute toggle failed:", err);
		}
	}, [client, roomId, isMuted]);

	const headerAvatarSrc = room.avatarUrl?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(room.avatarUrl.slice(6))}`
		: room.avatarUrl;
	const headerInitials = room.name.slice(0, 2).toUpperCase();

	// E2EE: Verschlüsselungsstatus prüfen (Lock grün/rot)
	const matrixRoom = client && roomId ? client.getRoom(roomId) : null;
	const isEncrypted = !!matrixRoom?.currentState.getStateEvents("m.room.encryption", "");

	return (
		<header className="flex items-center gap-3 px-4 h-[57px] border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
			{/* Raum-Avatar — klickbar → InfoPanel */}
			<button
				type="button"
				onClick={onSettingsOpen}
				className="shrink-0 cursor-pointer"
				title="Info öffnen"
			>
				<Avatar className="h-9 w-9">
					{headerAvatarSrc && <AvatarImage src={headerAvatarSrc} alt={room.name} />}
					<AvatarFallback className="text-xs font-semibold bg-muted">
						{headerInitials}
					</AvatarFallback>
				</Avatar>
			</button>

			{/* Raum-Name + Topic */}
			<div className="flex-1 min-w-0">
				<div className="flex items-center gap-1.5">
					{isEncrypted ? (
						<span title="Verschlüsselt">
							<Lock className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
						</span>
					) : (
						<span title="Nicht verschlüsselt">
							<LockOpen className="h-3.5 w-3.5 text-destructive/70 shrink-0" />
						</span>
					)}
					<span className="font-semibold text-sm truncate">{room.name}</span>
					<div className="flex items-center gap-1 text-[11px] text-muted-foreground shrink-0">
						<Users className="h-3 w-3" />
						<span>{room.memberCount}</span>
					</div>
				</div>
				{room.topic && <p className="text-xs text-muted-foreground truncate">{room.topic}</p>}
			</div>

			<div className="flex items-center gap-0.5">
				{/* UI-8: Suche */}
				{onSearchOpen && (
					<Button
						variant="ghost"
						size="icon"
						className="h-8 w-8"
						title="Nachrichten durchsuchen"
						onClick={onSearchOpen}
					>
						<Search className="h-4 w-4" />
					</Button>
				)}

				{/* UI-9: Mute/Unmute */}
				{client && roomId && (
					<Button
						variant="ghost"
						size="icon"
						className="h-8 w-8"
						title={isMuted ? "Benachrichtigungen aktivieren" : "Stummschalten"}
						onClick={toggleMute}
					>
						{isMuted ? <BellOff className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
					</Button>
				)}

				{/* UI-3: Einladen */}
				{client && roomId && (
					<InviteDialog
						client={client}
						roomId={roomId}
						trigger={
							<Button variant="ghost" size="icon" className="h-8 w-8" title="Benutzer einladen">
								<UserPlus className="h-4 w-4" />
							</Button>
						}
					/>
				)}

				{/* B-9: Call-Buttons (nur für DMs) */}
				{onCall && room.memberCount <= 2 && (
					<>
						<Button
							variant="ghost"
							size="icon"
							className="h-8 w-8"
							title="Sprachanruf"
							onClick={() => onCall(false)}
						>
							<Phone className="h-4 w-4" />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							className="h-8 w-8"
							title="Videoanruf"
							onClick={() => onCall(true)}
						>
							<Video className="h-4 w-4" />
						</Button>
					</>
				)}
			</div>
		</header>
	);
}
