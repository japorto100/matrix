"use client";

import { Bell, BellOff, Phone, Search, UserPlus, Users, Video } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
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

	return (
		<header className="flex items-center gap-3 px-4 py-3 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
			{/* Raum-Avatar */}
			<Avatar className="h-8 w-8 shrink-0">
				{headerAvatarSrc && <AvatarImage src={headerAvatarSrc} alt={room.name} />}
				<AvatarFallback className="text-xs font-semibold bg-muted">{headerInitials}</AvatarFallback>
			</Avatar>

			{/* Raum-Name */}
			<div className="flex-1 min-w-0">
				<button
					type="button"
					className="font-semibold text-sm truncate hover:underline cursor-pointer bg-transparent border-0 p-0 text-left"
					onClick={onSettingsOpen}
					title="Raumeinstellungen öffnen"
				>
					{room.name}
				</button>
				{room.topic && (
					<p className="text-xs text-muted-foreground truncate mt-0.5">{room.topic}</p>
				)}
			</div>

			<Separator orientation="vertical" className="h-6" />

			{/* Mitglieder-Anzahl */}
			<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
				<Users className="h-3.5 w-3.5" />
				<span>{room.memberCount}</span>
			</div>

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

			{/* Ungelesen Badge */}
			{room.unreadCount > 0 && (
				<Badge variant="destructive" className="text-[10px] px-1.5 py-0 h-5">
					{room.unreadCount > 99 ? "99+" : room.unreadCount}
				</Badge>
			)}
		</header>
	);
}
