"use client";

import { Ban, Camera, Lock, LockOpen, Pencil, ShieldBan, Trash2, UserMinus, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
	client: MatrixClient;
	roomId: string;
	onClose: () => void;
}

interface MemberInfo {
	userId: string;
	displayName: string;
	powerLevel: number;
	avatarUrl?: string;
}

function roleLabel(powerLevel: number): string {
	if (powerLevel >= 100) return "Admin";
	if (powerLevel >= 50) return "Moderator";
	return "Mitglied";
}

export function InfoPanel({ client, roomId, onClose }: Props) {
	const [roomName, setRoomName] = useState("");
	const [roomTopic, setRoomTopic] = useState("");
	const [members, setMembers] = useState<MemberInfo[]>([]);
	const [editingName, setEditingName] = useState(false);
	const [editingTopic, setEditingTopic] = useState(false);
	const [isLeaving, setIsLeaving] = useState(false);
	const [leaveConfirm, setLeaveConfirm] = useState(false);
	const [myPowerLevel, setMyPowerLevel] = useState(0);
	const [banConfirmId, setBanConfirmId] = useState<string | null>(null);
	const [isBlocked, setIsBlocked] = useState(false);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const avatarInputRef = useRef<HTMLInputElement>(null);

	const room = client.getRoom(roomId);
	const myUserId = client.getUserId() ?? "";
	const joinedMembers = room?.getJoinedMembers() ?? [];
	// DM-Erkennung: joined+invited Members ≤ 2 ODER getDMInviter() vorhanden
	const allMembers = [...joinedMembers, ...(room?.getMembersWithMembership("invite") ?? [])];
	const otherMember =
		allMembers.length === 2
			? allMembers.find((m) => m.userId !== myUserId)
			: joinedMembers.length === 2
				? joinedMembers.find((m) => m.userId !== myUserId)
				: undefined;
	const dmInviter = room?.getDMInviter();
	const isDM = !!otherMember || !!dmInviter;
	const isEncrypted = !!room?.currentState.getStateEvents("m.room.encryption", "");
	// Alle User können Name/Topic/Avatar bearbeiten (Matrix erlaubt es per Power-Level)

	// biome-ignore lint/correctness/useExhaustiveDependencies: room/otherMember sind abgeleitete Werte, deps auf roomId reicht
	useEffect(() => {
		if (!room) return;
		setRoomName(room.name || "");
		setRoomTopic(room.currentState.getStateEvents("m.room.topic", "")?.getContent()?.topic ?? "");
		// Block-Status prüfen (DM)
		if (otherMember) {
			const ignored = client.getIgnoredUsers?.() ?? [];
			setIsBlocked(ignored.includes(otherMember.userId));
		}
		setAvatarPreview(undefined);

		try {
			const powerLevels = room.currentState.getStateEvents("m.room.power_levels", "")?.getContent();
			const myPower = (powerLevels?.users as Record<string, number> | undefined)?.[myUserId] ?? 0;
			setMyPowerLevel(myPower);

			const joined = room.getJoinedMembers();
			const memberList: MemberInfo[] = joined.map((m) => {
				const mxcAvatar = m.getMxcAvatarUrl();
				return {
					userId: m.userId,
					displayName: m.name || m.userId,
					powerLevel: (powerLevels?.users as Record<string, number> | undefined)?.[m.userId] ?? 0,
					avatarUrl: mxcAvatar
						? `/api/matrix/media?mxc=${encodeURIComponent(mxcAvatar.slice(6))}`
						: undefined,
				};
			});
			memberList.sort(
				(a, b) => b.powerLevel - a.powerLevel || a.displayName.localeCompare(b.displayName),
			);
			setMembers(memberList);
		} catch (err) {
			console.error("[InfoPanel] load failed:", err);
		}
	}, [client, roomId, room, myUserId]);

	const saveName = useCallback(async () => {
		setEditingName(false);
		try {
			await client.setRoomName(roomId, roomName.trim());
		} catch {
			toast.error("Raumname konnte nicht gespeichert werden.");
		}
	}, [client, roomId, roomName]);

	const saveTopic = useCallback(async () => {
		setEditingTopic(false);
		try {
			await client.setRoomTopic(roomId, roomTopic.trim());
		} catch {
			toast.error("Thema konnte nicht gespeichert werden.");
		}
	}, [client, roomId, roomTopic]);

	const handleAvatarUpload = useCallback(
		async (e: React.ChangeEvent<HTMLInputElement>) => {
			const file = e.target.files?.[0];
			if (!file) return;
			e.target.value = "";
			setAvatarPreview(URL.createObjectURL(file));
			try {
				const upload = await client.uploadContent(file);
				await (
					client.sendStateEvent as (r: string, t: string, c: unknown, s: string) => Promise<unknown>
				)(roomId, "m.room.avatar", { url: upload.content_uri }, "");
			} catch {
				toast.error("Avatar konnte nicht gesetzt werden.");
				setAvatarPreview(undefined);
			}
		},
		[client, roomId],
	);

	const kickMember = useCallback(
		async (userId: string) => {
			try {
				const token = client.getAccessToken();
				const base = client.baseUrl;
				const rid = encodeURIComponent(roomId);
				const res = await fetch(`${base}/_matrix/client/v3/rooms/${rid}/kick`, {
					method: "POST",
					headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
					body: JSON.stringify({ user_id: userId, reason: "Entfernt durch Moderator" }),
				});
				if (res.ok) {
					setMembers((prev) => prev.filter((m) => m.userId !== userId));
					toast.success("Benutzer entfernt.");
				} else {
					toast.error("Benutzer konnte nicht entfernt werden.");
				}
			} catch {
				toast.error("Verbindungsfehler.");
			}
		},
		[client, roomId],
	);

	const banMember = useCallback(
		async (userId: string) => {
			try {
				const token = client.getAccessToken();
				const base = client.baseUrl;
				const rid = encodeURIComponent(roomId);
				const res = await fetch(`${base}/_matrix/client/v3/rooms/${rid}/ban`, {
					method: "POST",
					headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
					body: JSON.stringify({ user_id: userId, reason: "Gesperrt durch Moderator" }),
				});
				if (res.ok) {
					setMembers((prev) => prev.filter((m) => m.userId !== userId));
					setBanConfirmId(null);
					toast.success("Benutzer gesperrt.");
				} else {
					toast.error("Benutzer konnte nicht gesperrt werden.");
				}
			} catch {
				toast.error("Verbindungsfehler.");
			}
		},
		[client, roomId],
	);

	const toggleBlockUser = useCallback(async () => {
		if (!otherMember) return;
		try {
			const token = client.getAccessToken();
			const base = client.baseUrl;
			const uid = encodeURIComponent(myUserId);
			// Aktuelle Ignore-Liste holen
			const res = await fetch(
				`${base}/_matrix/client/v3/user/${uid}/account_data/m.ignored_user_list`,
				{
					headers: { Authorization: `Bearer ${token}` },
				},
			);
			const current = res.ok ? await res.json() : { ignored_users: {} };
			const ignoredUsers = current.ignored_users ?? {};

			if (isBlocked) {
				delete ignoredUsers[otherMember.userId];
			} else {
				ignoredUsers[otherMember.userId] = {};
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
	}, [client, myUserId, otherMember, isBlocked]);

	const leaveOrDelete = useCallback(async () => {
		setIsLeaving(true);
		try {
			const matrixRoom = client.getRoom(roomId);
			const membership = matrixRoom?.getMyMembership();
			if (membership !== "join") {
				client.store.removeRoom(roomId);
				onClose();
				return;
			}
			const token = client.getAccessToken();
			const base = client.baseUrl;
			const rid = encodeURIComponent(roomId);
			// Admin + Gruppe → alle kicken
			if (!isDM && myPowerLevel >= 100) {
				for (const m of members) {
					if (m.userId !== myUserId) {
						await fetch(`${base}/_matrix/client/v3/rooms/${rid}/kick`, {
							method: "POST",
							headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
							body: JSON.stringify({ user_id: m.userId, reason: "Raum gelöscht" }),
						}).catch(() => {});
					}
				}
			}
			// Leave
			const leaveRes = await fetch(`${base}/_matrix/client/v3/rooms/${rid}/leave`, {
				method: "POST",
				headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
				body: "{}",
			});
			if (!leaveRes.ok) {
				toast.error("Verlassen fehlgeschlagen.");
				return;
			}
			// Forget
			await fetch(`${base}/_matrix/client/v3/rooms/${rid}/forget`, {
				method: "POST",
				headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
				body: "{}",
			}).catch(() => {});
			// Aus SDK Store entfernen + Event emittern
			client.store.removeRoom(roomId);
			client.emit("deleteRoom" as any, roomId);
			onClose();
		} catch {
			toast.error("Raum konnte nicht verlassen werden.");
		} finally {
			setIsLeaving(false);
		}
	}, [client, roomId, onClose, isDM, myPowerLevel, members, myUserId]);

	const dmUserId = otherMember?.userId ?? dmInviter;
	const displayName = isDM
		? (otherMember?.name ?? dmUserId ?? room?.name ?? "")
		: (room?.name ?? "");
	const initials = displayName.slice(0, 2).toUpperCase() || "?";
	const mxcAvatar = isDM ? otherMember?.getMxcAvatarUrl() : room?.getMxcAvatarUrl();
	const avatarSrc =
		avatarPreview ??
		(mxcAvatar ? `/api/matrix/media?mxc=${encodeURIComponent(mxcAvatar.slice(6))}` : undefined);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border bg-background overflow-hidden">
			{/* Header — exakt gleiche Höhe wie RoomHeader */}
			<div className="flex items-center justify-between h-[57px] px-4 border-b border-border bg-background shrink-0">
				<span className="text-sm font-semibold">{isDM ? "Info" : "Raum Info"}</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<div className="flex-1 overflow-y-auto p-4 space-y-5">
				{/* Avatar + Name */}
				<div className="flex flex-col items-center text-center gap-2">
					<div className="relative">
						<Avatar className="h-[72px] w-[72px]">
							{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
							<AvatarFallback className="text-lg font-semibold bg-muted">{initials}</AvatarFallback>
						</Avatar>
						{/* Avatar-Upload für Räume */}
						{!isDM && (
							<>
								<button
									type="button"
									className="absolute bottom-0 right-0 h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
									title="Raum-Avatar ändern"
									onClick={() => avatarInputRef.current?.click()}
								>
									<Camera className="h-3.5 w-3.5" />
								</button>
								<input
									ref={avatarInputRef}
									type="file"
									accept="image/*"
									className="hidden"
									onChange={handleAvatarUpload}
								/>
							</>
						)}
					</div>
					<div className="w-full">
						{/* Name — inline editierbar für Räume */}
						{!isDM && editingName ? (
							<input
								type="text"
								value={roomName}
								onChange={(e) => setRoomName(e.target.value)}
								onKeyDown={(e) => {
									if (e.key === "Enter") saveName();
									if (e.key === "Escape") setEditingName(false);
								}}
								onBlur={saveName}
								autoFocus
								className="w-full text-center font-semibold text-base bg-transparent border-b border-primary outline-none"
							/>
						) : (
							<div className="flex items-center justify-center gap-1">
								<p className="font-semibold text-base">{displayName}</p>
								{!isDM && (
									<button
										type="button"
										onClick={() => setEditingName(true)}
										className="text-muted-foreground hover:text-foreground transition-colors"
									>
										<Pencil className="h-3 w-3" />
									</button>
								)}
							</div>
						)}
						{isDM && dmUserId && (
							<p className="text-xs text-muted-foreground text-center">{dmUserId}</p>
						)}
						{!isDM && (
							<p className="text-xs text-muted-foreground text-center mt-0.5">
								{members.length} Mitglieder
							</p>
						)}
					</div>
					{/* E2EE Status */}
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

				{/* DM: Block User */}
				{isDM && otherMember && (
					<button
						type="button"
						onClick={toggleBlockUser}
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
				)}

				{/* Thema — inline editierbar */}
				{!isDM && (
					<div>
						<div className="flex items-center gap-1 mb-1">
							<label className="text-xs font-medium text-muted-foreground">Thema</label>
							{!editingTopic && (
								<button
									type="button"
									onClick={() => setEditingTopic(true)}
									className="text-muted-foreground hover:text-foreground transition-colors"
								>
									<Pencil className="h-2.5 w-2.5" />
								</button>
							)}
						</div>
						{editingTopic ? (
							<textarea
								value={roomTopic}
								onChange={(e) => setRoomTopic(e.target.value)}
								onKeyDown={(e) => {
									if (e.key === "Enter" && !e.shiftKey) {
										e.preventDefault();
										saveTopic();
									}
									if (e.key === "Escape") setEditingTopic(false);
								}}
								onBlur={saveTopic}
								rows={2}
								placeholder="Worum geht es in diesem Raum?"
								autoFocus
								className="w-full rounded-lg border border-primary bg-muted/30 px-3 py-1.5 text-sm resize-none placeholder:text-muted-foreground/60 focus:outline-none"
							/>
						) : (
							<p
								className="text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
								onClick={() => setEditingTopic(true)}
							>
								{roomTopic || "Thema hinzufügen…"}
							</p>
						)}
					</div>
				)}

				{/* Mitgliederliste — nur im Room-Modus */}
				{!isDM && (
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-2 block">
							Mitglieder ({members.length})
						</label>
						<div className="flex flex-col gap-1.5">
							{members.map((member) => {
								const memberInitials = member.displayName.slice(0, 2).toUpperCase();
								const isMe = member.userId === myUserId;
								const canModerate = myPowerLevel >= 50 && !isMe && member.powerLevel < myPowerLevel;
								return (
									<div
										key={member.userId}
										className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-muted/50 transition-colors group/member"
									>
										<Avatar className="h-7 w-7 shrink-0">
											{member.avatarUrl && (
												<AvatarImage src={member.avatarUrl} alt={member.displayName} />
											)}
											<AvatarFallback className="text-[10px] font-semibold bg-muted text-muted-foreground">
												{memberInitials}
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
				)}
			</div>

			{/* Footer — gleiche Höhe wie Composer (p-3 border-t border-border/50) */}
			<div className="p-3 border-t border-border shrink-0">
				{leaveConfirm ? (
					<div className="flex items-center gap-2">
						<span className="text-xs text-muted-foreground flex-1">
							{isDM
								? "Chat wirklich löschen?"
								: myPowerLevel >= 100
									? "Raum wirklich löschen?"
									: "Raum wirklich verlassen?"}
						</span>
						<Button size="sm" variant="ghost" onClick={() => setLeaveConfirm(false)}>
							Abbrechen
						</Button>
						<Button size="sm" variant="destructive" onClick={leaveOrDelete} disabled={isLeaving}>
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
						{isDM ? "Chat löschen" : myPowerLevel >= 100 ? "Raum löschen" : "Raum verlassen"}
					</Button>
				)}
			</div>
		</div>
	);
}
