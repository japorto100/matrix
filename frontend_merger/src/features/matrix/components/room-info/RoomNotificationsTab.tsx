"use client";

import { useRoomNotificationMode } from "@matrix/lib/hooks/useRoomNotificationMode";
import type { RoomNotificationMode } from "@matrix/lib/notificationMode";
import { AtSign, Bell, BellOff, Check, Server } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { cn } from "@/lib/utils";

interface Props {
	client: MatrixClient;
	roomId: string;
}

interface ModeCardData {
	mode: RoomNotificationMode;
	title: string;
	description: string;
	icon: typeof Bell;
}

const MODE_CARDS: ModeCardData[] = [
	{
		mode: "default",
		title: "Standard",
		description: "Folge der globalen Benachrichtigungs-Einstellung.",
		icon: Server,
	},
	{
		mode: "all",
		title: "Alle Nachrichten",
		description: "Jede Nachricht benachrichtigt dich, mit Ton.",
		icon: Bell,
	},
	{
		mode: "mentions_keywords",
		title: "Nur Erwähnungen & Stichwörter",
		description:
			"Generelle Nachrichten sind stumm. Nur @-Erwähnungen und deine Stichwörter lösen eine Benachrichtigung aus.",
		icon: AtSign,
	},
	{
		mode: "mute",
		title: "Stumm",
		description: "Absolut keine Benachrichtigungen — auch nicht bei Erwähnungen.",
		icon: BellOff,
	},
];

/**
 * Notifications-Tab im RoomInfoPanel (G4).
 *
 * Zeigt 4 auswaehlbare Mode-Cards; klick setzt den Mode via
 * `useRoomNotificationMode`. Nachher folgt Keyword-Editor (globaler Scope,
 * gehoert eher in die App-Settings als pro Room).
 */
export function RoomNotificationsTab({ client, roomId }: Props) {
	const { mode, isSetting, setMode } = useRoomNotificationMode(client, roomId);

	return (
		<div className="space-y-2">
			<p className="text-xs text-muted-foreground">
				Waehle wie Nachrichten in diesem Raum dich benachrichtigen sollen. Die Einstellung
				synchronisiert mit deinem Account (wirkt auf allen Geraeten).
			</p>
			<div className="flex flex-col gap-2">
				{MODE_CARDS.map((card) => {
					const Icon = card.icon;
					const isActive = mode === card.mode;
					return (
						<button
							key={card.mode}
							type="button"
							disabled={isSetting || isActive}
							onClick={() => {
								void setMode(card.mode);
							}}
							className={cn(
								"flex items-start gap-3 rounded-lg border p-3 text-left transition-colors",
								isActive
									? "border-primary bg-primary/5"
									: "border-border/50 hover:border-border hover:bg-muted/30",
								isSetting && "opacity-60 cursor-wait",
							)}
						>
							<Icon
								className={cn(
									"h-4 w-4 shrink-0 mt-0.5",
									isActive ? "text-primary" : "text-muted-foreground",
								)}
							/>
							<div className="min-w-0 flex-1">
								<div className="text-sm font-medium">{card.title}</div>
								<div className="text-xs text-muted-foreground mt-0.5">{card.description}</div>
							</div>
							{isActive && <Check className="h-3.5 w-3.5 shrink-0 text-primary mt-1" />}
						</button>
					);
				})}
			</div>
		</div>
	);
}
