"use client";

import { Shield } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { toast } from "sonner";
import type { MemberInfo } from "@/lib/matrix/hooks/useRoomMembers";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

interface RoleProps {
	members: MemberInfo[];
	myUserId: string;
	client: MatrixClient;
	roomId: string;
}

export function RoleManagement({ members, myUserId, client, roomId }: RoleProps) {
	return (
		<div>
			<label className="text-xs font-medium text-muted-foreground mb-2 block">
				Rollen verwalten
			</label>
			<div className="flex flex-col gap-1">
				{members
					.filter((m) => m.userId !== myUserId)
					.map((member) => (
						<div
							key={`role-${member.userId}`}
							className="flex items-center justify-between px-2 py-1 rounded hover:bg-muted/50"
						>
							<span className="text-xs truncate flex-1">{member.displayName}</span>
							<Select
								value={String(member.powerLevel)}
								onValueChange={(val) => {
									client
										.setPowerLevel(roomId, member.userId, Number.parseInt(val))
										.catch(() => toast.error("Rolle ändern fehlgeschlagen"));
								}}
							>
								<SelectTrigger className="h-6 w-[100px] text-[10px]">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="0">Member</SelectItem>
									<SelectItem value="50">Moderator</SelectItem>
									<SelectItem value="100">Admin</SelectItem>
								</SelectContent>
							</Select>
						</div>
					))}
			</div>
		</div>
	);
}

interface PermissionsProps {
	powerLevelsContent: Record<string, unknown> | undefined;
	client: MatrixClient;
	roomId: string;
}

export function PermissionsPanel({ powerLevelsContent, client, roomId }: PermissionsProps) {
	const settings = [
		{ key: "events_default", label: "Nachrichten senden" },
		{ key: "invite", label: "Einladen" },
		{ key: "state_default", label: "Raum-Info ändern" },
	];

	return (
		<div>
			<label className="text-xs font-medium text-muted-foreground mb-2 block">
				<Shield className="h-3 w-3 inline mr-1" />
				Berechtigungen
			</label>
			<div className="space-y-2 text-xs">
				{settings.map(({ key, label }) => {
					const currentLevel =
						((powerLevelsContent ?? {}) as Record<string, number>)[key] ??
						(key === "state_default" ? 50 : 0);
					return (
						<div key={key} className="flex items-center justify-between">
							<span className="text-muted-foreground">{label}</span>
							<Select
								value={String(currentLevel)}
								onValueChange={(val) => {
									const level = Number.parseInt(val);
									const newPL = { ...(powerLevelsContent ?? {}), [key]: level };
									client
										// biome-ignore lint/suspicious/noExplicitAny: power_levels typing
										.sendStateEvent(roomId, "m.room.power_levels" as any, newPL, "")
										.catch(() => toast.error("Berechtigung ändern fehlgeschlagen"));
								}}
							>
								<SelectTrigger className="h-6 w-[110px] text-[10px]">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="0">Alle</SelectItem>
									<SelectItem value="50">Moderator+</SelectItem>
									<SelectItem value="100">Admin</SelectItem>
								</SelectContent>
							</Select>
						</div>
					);
				})}
			</div>
		</div>
	);
}
