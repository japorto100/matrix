"use client";

import { Ban, LogOut, Save, UserMinus, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Props {
	client: MatrixClient;
	roomId: string;
	onClose: () => void;
}

interface MemberInfo {
	userId: string;
	displayName: string;
	powerLevel: number;
}

function roleLabel(powerLevel: number): string {
	if (powerLevel >= 100) return "Admin";
	if (powerLevel >= 50) return "Moderator";
	return "Mitglied";
}

export function RoomSettingsPanel({ client, roomId, onClose }: Props) {
	const [roomName, setRoomName] = useState("");
	const [roomTopic, setRoomTopic] = useState("");
	const [members, setMembers] = useState<MemberInfo[]>([]);
	const [isSavingName, setIsSavingName] = useState(false);
	const [isSavingTopic, setIsSavingTopic] = useState(false);
	const [isLeaving, setIsLeaving] = useState(false);
	const [leaveConfirm, setLeaveConfirm] = useState(false);
	const [myPowerLevel, setMyPowerLevel] = useState(0);
	const [banConfirmId, setBanConfirmId] = useState<string | null>(null);

	// Raum-Daten laden
	useEffect(() => {
		const room = client.getRoom(roomId);
		if (!room) return;

		setRoomName(room.name || "");
		setRoomTopic(room.currentState.getStateEvents("m.room.topic", "")?.getContent()?.topic ?? "");

		try {
			const myUserId = client.getUserId() ?? "";
			const powerLevels = room.currentState.getStateEvents("m.room.power_levels", "")?.getContent();
			const myPower = (powerLevels?.users as Record<string, number> | undefined)?.[myUserId] ?? 0;
			setMyPowerLevel(myPower);

			const joined = room.getJoinedMembers();
			const memberList: MemberInfo[] = joined.map((m) => ({
				userId: m.userId,
				displayName: m.name || m.userId,
				powerLevel: (powerLevels?.users as Record<string, number> | undefined)?.[m.userId] ?? 0,
			}));
			memberList.sort(
				(a, b) => b.powerLevel - a.powerLevel || a.displayName.localeCompare(b.displayName),
			);
			setMembers(memberList);
		} catch (err) {
			console.error("[RoomSettingsPanel] members load failed:", err);
		}
	}, [client, roomId]);

	const saveName = useCallback(async () => {
		setIsSavingName(true);
		try {
			await client.setRoomName(roomId, roomName.trim());
		} catch (err) {
			console.error("[RoomSettingsPanel] save name failed:", err);
		} finally {
			setIsSavingName(false);
		}
	}, [client, roomId, roomName]);

	const saveTopic = useCallback(async () => {
		setIsSavingTopic(true);
		try {
			await client.setRoomTopic(roomId, roomTopic.trim());
		} catch (err) {
			console.error("[RoomSettingsPanel] save topic failed:", err);
		} finally {
			setIsSavingTopic(false);
		}
	}, [client, roomId, roomTopic]);

	// UI-10: Kick
	const kickMember = useCallback(
		async (userId: string) => {
			try {
				await client.kick(roomId, userId, "Entfernt durch Moderator");
				setMembers((prev) => prev.filter((m) => m.userId !== userId));
			} catch (err) {
				console.error("[RoomSettingsPanel] kick failed:", err);
			}
		},
		[client, roomId],
	);

	// UI-10: Ban
	const banMember = useCallback(
		async (userId: string) => {
			try {
				await client.ban(roomId, userId, "Gesperrt durch Moderator");
				setMembers((prev) => prev.filter((m) => m.userId !== userId));
				setBanConfirmId(null);
			} catch (err) {
				console.error("[RoomSettingsPanel] ban failed:", err);
			}
		},
		[client, roomId],
	);

	const leaveRoom = useCallback(async () => {
		setIsLeaving(true);
		try {
			await client.leave(roomId);
			onClose();
		} catch (err) {
			console.error("[RoomSettingsPanel] leave failed:", err);
		} finally {
			setIsLeaving(false);
		}
	}, [client, roomId, onClose]);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l bg-background overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
				<span className="text-sm font-semibold">Raumeinstellungen</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			{/* Inhalte */}
			<div className="flex-1 overflow-y-auto p-4 space-y-5">
				{/* Raumname */}
				<div>
					<label className="text-xs font-medium text-muted-foreground mb-1 block">Raumname</label>
					<div className="flex gap-2">
						<input
							type="text"
							value={roomName}
							onChange={(e) => setRoomName(e.target.value)}
							className="flex-1 rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
						/>
						<Button size="sm" variant="outline" onClick={saveName} disabled={isSavingName}>
							<Save className="h-3.5 w-3.5 mr-1" />
							{isSavingName ? "…" : "Speichern"}
						</Button>
					</div>
				</div>

				{/* Thema */}
				<div>
					<label className="text-xs font-medium text-muted-foreground mb-1 block">Thema</label>
					<div className="flex flex-col gap-2">
						<textarea
							value={roomTopic}
							onChange={(e) => setRoomTopic(e.target.value)}
							rows={3}
							className="w-full rounded-md border bg-background px-3 py-1.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
						/>
						<Button
							size="sm"
							variant="outline"
							onClick={saveTopic}
							disabled={isSavingTopic}
							className="self-end"
						>
							<Save className="h-3.5 w-3.5 mr-1" />
							{isSavingTopic ? "…" : "Speichern"}
						</Button>
					</div>
				</div>

				{/* Mitgliederliste */}
				<div>
					<label className="text-xs font-medium text-muted-foreground mb-2 block">
						Mitglieder ({members.length})
					</label>
					<div className="flex flex-col gap-1.5">
						{members.map((member) => {
							const initials = member.displayName.slice(0, 2).toUpperCase();
							const isMe = member.userId === client.getUserId();
							const canModerate = myPowerLevel >= 50 && !isMe && member.powerLevel < myPowerLevel;
							return (
								<div
									key={member.userId}
									className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-muted/50 transition-colors group/member"
								>
									<Avatar className="h-7 w-7 shrink-0">
										<AvatarFallback className="text-[10px] font-semibold bg-muted text-muted-foreground">
											{initials}
										</AvatarFallback>
									</Avatar>
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium truncate">{member.displayName}</p>
										<p className="text-[10px] text-muted-foreground truncate">{member.userId}</p>
									</div>
									{member.powerLevel > 0 && (
										<Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 shrink-0">
											{roleLabel(member.powerLevel)}
										</Badge>
									)}
									{/* UI-10: Moderation */}
									{canModerate && (
										<div className="flex items-center gap-0.5 opacity-0 group-hover/member:opacity-100 transition-opacity shrink-0">
											{banConfirmId === member.userId ? (
												<div className="flex items-center gap-1">
													<span className="text-[10px] text-destructive">Sperren?</span>
													<Button
														variant="ghost"
														size="icon"
														className="h-6 w-6"
														onClick={() => setBanConfirmId(null)}
													>
														<X className="h-3 w-3" />
													</Button>
													<Button
														variant="ghost"
														size="icon"
														className="h-6 w-6 text-destructive hover:bg-destructive/20"
														onClick={() => banMember(member.userId)}
														title="Bestätigen"
													>
														<Ban className="h-3 w-3" />
													</Button>
												</div>
											) : (
												<>
													<Button
														variant="ghost"
														size="icon"
														className="h-6 w-6 text-muted-foreground hover:text-foreground"
														onClick={() => kickMember(member.userId)}
														title="Entfernen"
													>
														<UserMinus className="h-3 w-3" />
													</Button>
													<Button
														variant="ghost"
														size="icon"
														className="h-6 w-6 text-muted-foreground hover:text-destructive"
														onClick={() => setBanConfirmId(member.userId)}
														title="Sperren"
													>
														<Ban className="h-3 w-3" />
													</Button>
												</>
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>
				</div>
			</div>

			{/* Raum verlassen */}
			<div className="p-4 border-t shrink-0">
				{leaveConfirm ? (
					<div className="flex items-center gap-2">
						<span className="text-xs text-muted-foreground flex-1">Wirklich verlassen?</span>
						<Button size="sm" variant="ghost" onClick={() => setLeaveConfirm(false)}>
							Abbrechen
						</Button>
						<Button size="sm" variant="destructive" onClick={leaveRoom} disabled={isLeaving}>
							{isLeaving ? "…" : "Verlassen"}
						</Button>
					</div>
				) : (
					<Button
						variant="outline"
						className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive"
						onClick={() => setLeaveConfirm(true)}
					>
						<LogOut className="h-4 w-4 mr-2" />
						Raum verlassen
					</Button>
				)}
			</div>
		</div>
	);
}
