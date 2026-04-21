"use client";

import {
	type UseRoomNotificationModeReturn,
	useRoomNotificationMode,
} from "@matrix/lib/hooks/useRoomNotificationMode";
import type { RoomNotificationMode } from "@matrix/lib/notificationMode";
import { AtSign, Bell, BellOff, Check, Server } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ModeEntry {
	mode: RoomNotificationMode;
	label: string;
	description: string;
	icon: typeof Bell;
}

const MODES: ModeEntry[] = [
	{
		mode: "default",
		label: "Standard",
		description: "Server-Einstellung fuer diesen Raum",
		icon: Server,
	},
	{
		mode: "all",
		label: "Alle Nachrichten",
		description: "Jede Nachricht benachrichtigt (mit Ton)",
		icon: Bell,
	},
	{
		mode: "mentions_keywords",
		label: "Nur Erwaehnungen & Stichwoerter",
		description: "Generelle Nachrichten stumm, Erwaehnungen benachrichtigen",
		icon: AtSign,
	},
	{
		mode: "mute",
		label: "Stumm",
		description: "Keine Benachrichtigungen, auch nicht bei Erwaehnungen",
		icon: BellOff,
	},
];

export function modeIcon(mode: RoomNotificationMode) {
	return MODES.find((m) => m.mode === mode)?.icon ?? Bell;
}

export function modeLabel(mode: RoomNotificationMode): string {
	return MODES.find((m) => m.mode === mode)?.label ?? "Standard";
}

interface SwitcherProps {
	hook: UseRoomNotificationModeReturn;
	trigger?: React.ReactNode;
	/** Kompakt: nur Icon im Trigger, kein Label. */
	compact?: boolean;
}

/**
 * Dropdown-Menu mit 4 Modes. Trigger ist custom uebergebbar (z.B. fuer
 * Room-Header-Button, Context-Menu-Item-Wrapper, RoomInfoPanel-Sektion).
 *
 * Nutzt den bereits aufgerufenen `useRoomNotificationMode`-Hook via Prop
 * (spart doppelten Account-Data-Listener, wenn die Parent-Komponente den
 * hook schon fuer andere Zwecke hat).
 */
export function RoomNotificationSwitcher({ hook, trigger, compact }: SwitcherProps) {
	const { mode, isSetting, setMode } = hook;
	const CurrentIcon = modeIcon(mode);

	const defaultTrigger = (
		<button
			type="button"
			disabled={isSetting}
			className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border/40 hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
		>
			<CurrentIcon className="h-4 w-4" />
			{!compact && <span>{modeLabel(mode)}</span>}
		</button>
	);

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>{trigger ?? defaultTrigger}</DropdownMenuTrigger>
			<DropdownMenuContent align="end" className="w-72">
				{MODES.map((entry) => {
					const Icon = entry.icon;
					const isActive = mode === entry.mode;
					return (
						<DropdownMenuItem
							key={entry.mode}
							onSelect={() => {
								void setMode(entry.mode);
							}}
							className="py-2 cursor-pointer"
						>
							<Icon className="h-4 w-4 mr-2 shrink-0 mt-0.5 text-muted-foreground" />
							<div className="min-w-0 flex-1">
								<div className="text-sm font-medium">{entry.label}</div>
								<div className="text-[11px] text-muted-foreground">{entry.description}</div>
							</div>
							{isActive && <Check className="h-3.5 w-3.5 ml-2 shrink-0 text-primary" />}
						</DropdownMenuItem>
					);
				})}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

/**
 * Convenience-Wrapper: Hook + Switcher zusammen, fuer Orte die kein separates
 * Hook-Instanziieren brauchen.
 */
export function RoomNotificationSwitcherStandalone({
	client,
	roomId,
	trigger,
	compact,
}: {
	client: MatrixClient;
	roomId: string;
	trigger?: React.ReactNode;
	compact?: boolean;
}) {
	const hook = useRoomNotificationMode(client, roomId);
	return <RoomNotificationSwitcher hook={hook} trigger={trigger} compact={compact} />;
}
