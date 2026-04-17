"use client";

import type { RoomInfo } from "@matrix/lib/types";
import { hashColor } from "@matrix/lib/utils";
import { Check, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const AVATAR_COLORS = [
	"bg-blue-500",
	"bg-emerald-500",
	"bg-violet-500",
	"bg-amber-500",
	"bg-rose-500",
	"bg-cyan-500",
	"bg-indigo-500",
	"bg-pink-500",
];
const avatarColor = (name: string) => hashColor(name, AVATAR_COLORS);

interface Props {
	room: RoomInfo;
	client?: MatrixClient | null;
	onSelect: (roomId: string) => void;
}

export function InviteItem({ room, client, onSelect }: Props) {
	const initials = room.name.slice(0, 2).toUpperCase();
	const isDM = !!room.dmUserId;

	const handleAccept = async () => {
		if (!client) return;
		try {
			await client.joinRoom(room.roomId);
			toast.success(isDM ? `Chat mit ${room.name} gestartet.` : `${room.name} beigetreten.`);
			onSelect(room.roomId);
		} catch {
			toast.error("Beitreten fehlgeschlagen.");
		}
	};

	const handleDecline = async () => {
		if (!client) return;
		try {
			await client.leave(room.roomId);
			await client.forget(room.roomId).catch(() => {});
			toast.success("Einladung abgelehnt.");
		} catch {
			toast.error("Ablehnen fehlgeschlagen.");
		}
	};

	return (
		<div className="flex items-center gap-3 px-2.5 py-2 rounded-lg bg-primary/5 border-l-2 border-primary">
			<Avatar className="h-9 w-9 shrink-0">
				<AvatarFallback className={cn("text-xs font-semibold text-white", avatarColor(room.name))}>
					{initials}
				</AvatarFallback>
			</Avatar>
			<div className="flex-1 min-w-0">
				<p className="text-sm font-medium truncate">{room.name}</p>
				<p className="text-[10px] text-primary">{isDM ? "Direktnachricht" : "Gruppen-Einladung"}</p>
			</div>
			<div className="flex items-center gap-1 shrink-0">
				<Button
					variant="ghost"
					size="icon"
					className="h-7 w-7 text-emerald-500 hover:bg-emerald-500/20"
					onClick={handleAccept}
					title="Annehmen"
				>
					<Check className="h-4 w-4" />
				</Button>
				<Button
					variant="ghost"
					size="icon"
					className="h-7 w-7 text-destructive hover:bg-destructive/20"
					onClick={handleDecline}
					title="Ablehnen"
				>
					<X className="h-4 w-4" />
				</Button>
			</div>
		</div>
	);
}
