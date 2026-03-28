"use client";

import {
	Ban,
	Bell,
	BellOff,
	Camera,
	Check,
	Copy,
	FileText,
	Image,
	Link2,
	Lock,
	LockOpen,
	Pencil,
	Pin,
	Shield,
	Trash2,
	UserMinus,
	X,
} from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { RoomStateEvent } from "matrix-js-sdk";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
	avatarUrl?: string;
}

function roleLabel(powerLevel: number): string {
	if (powerLevel >= 100) return "Admin";
	if (powerLevel >= 50) return "Moderator";
	return "Mitglied";
}

export function RoomInfoPanel({ client, roomId, onClose }: Props) {
	const [roomName, setRoomName] = useState("");
	const [roomTopic, setRoomTopic] = useState("");
	const [members, setMembers] = useState<MemberInfo[]>([]);
	const [editingName, setEditingName] = useState(false);
	const [editingTopic, setEditingTopic] = useState(false);
	const [isLeaving, setIsLeaving] = useState(false);
	const [leaveConfirm, setLeaveConfirm] = useState(false);
	const [banConfirmId, setBanConfirmId] = useState<string | null>(null);
	const [isMuted, setIsMuted] = useState(false);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const [pinnedIds, setPinnedIds] = useState<string[]>([]);
	const avatarInputRef = useRef<HTMLInputElement>(null);

	const room = client.getRoom(roomId);
	const myUserId = client.getUserId() ?? "";
	const membership = room?.getMyMembership() ?? "leave";
	const isEncrypted = !!room?.currentState.getStateEvents("m.room.encryption", "");
	// Power-Level: direkt aus currentState lesen (kein useState-Lag)
	const powerLevelsContent = room?.currentState
		.getStateEvents("m.room.power_levels", "")
		?.getContent();
	const myPowerLevel =
		(powerLevelsContent?.users as Record<string, number> | undefined)?.[myUserId] ?? 0;
	const stateDefault = (powerLevelsContent?.state_default as number) ?? 50;
	const canEditRoomInfo = myPowerLevel >= stateDefault;

	// biome-ignore lint/correctness/useExhaustiveDependencies: room ist abgeleiteter Wert
	useEffect(() => {
		if (!room) return;
		setRoomName(room.name || "");
		setRoomTopic(room.currentState.getStateEvents("m.room.topic", "")?.getContent()?.topic ?? "");
		setAvatarPreview(undefined);

		// Members via API laden (SDK-Cache hat bei Sliding Sync nicht alle)
		// powerLevelsContent aus currentState für Member-Liste (Snapshot zum Ladezeitpunkt)
		const plContent = room.currentState.getStateEvents("m.room.power_levels", "")?.getContent();
		(async () => {
			try {
				const token = client.getAccessToken();
				const res = await fetch(
					`${client.baseUrl}/_matrix/client/v3/rooms/${encodeURIComponent(roomId)}/joined_members`,
					{ headers: { Authorization: `Bearer ${token}` } },
				);
				if (!res.ok) throw new Error("members fetch failed");
				const data = await res.json();
				const joined =
					(data.joined as Record<string, { display_name?: string; avatar_url?: string }>) ?? {};
				const memberList: MemberInfo[] = Object.entries(joined).map(([userId, info]) => ({
					userId,
					displayName: info.display_name || userId.split(":")[0]?.replace("@", "") || userId,
					powerLevel: (plContent?.users as Record<string, number> | undefined)?.[userId] ?? 0,
					avatarUrl: info.avatar_url?.startsWith("mxc://")
						? `/api/matrix/media?mxc=${encodeURIComponent(info.avatar_url.slice(6))}`
						: undefined,
				}));
				memberList.sort(
					(a, b) => b.powerLevel - a.powerLevel || a.displayName.localeCompare(b.displayName),
				);
				setMembers(memberList);
			} catch {
				// Fallback: SDK-Cache
				const joined = room.getJoinedMembers();
				const memberList: MemberInfo[] = joined.map((m) => ({
					userId: m.userId,
					displayName: m.name || m.userId,
					powerLevel: (plContent?.users as Record<string, number> | undefined)?.[m.userId] ?? 0,
					avatarUrl: m.getMxcAvatarUrl()?.startsWith("mxc://")
						? `/api/matrix/media?mxc=${encodeURIComponent(m.getMxcAvatarUrl()!.slice(6))}`
						: undefined,
				}));
				memberList.sort(
					(a, b) => b.powerLevel - a.powerLevel || a.displayName.localeCompare(b.displayName),
				);
				setMembers(memberList);
			}
		})();
	}, [client, roomId, myUserId]);

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

	// Gepinnte Nachrichten: State + Live-Listener damit InfoPanel bei Pin/Unpin neu rendert
	useEffect(() => {
		if (!room) return;
		const readPinned = () => {
			const pinned: string[] =
				room.currentState.getStateEvents("m.room.pinned_events", "")?.getContent()?.pinned ?? [];
			setPinnedIds(pinned);
		};
		readPinned();
		const handler = (_event: unknown, _room: unknown, type: string) => {
			if (type === "m.room.pinned_events") readPinned();
		};
		client.on(RoomStateEvent.Events, handler as any);
		return () => {
			client.off(RoomStateEvent.Events, handler as any);
		};
	}, [client, room, roomId]);

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
				await client.kick(roomId, userId, "Entfernt durch Moderator");
				setMembers((prev) => prev.filter((m) => m.userId !== userId));
				toast.success("Benutzer entfernt.");
			} catch {
				toast.error("Benutzer konnte nicht entfernt werden.");
			}
		},
		[client, roomId],
	);

	const banMember = useCallback(
		async (userId: string) => {
			try {
				await client.ban(roomId, userId, "Gesperrt durch Moderator");
				setMembers((prev) => prev.filter((m) => m.userId !== userId));
				setBanConfirmId(null);
				toast.success("Benutzer gesperrt.");
			} catch {
				toast.error("Benutzer konnte nicht gesperrt werden.");
			}
		},
		[client, roomId],
	);

	const leaveOrDelete = useCallback(async () => {
		setIsLeaving(true);
		try {
			if (myPowerLevel >= 100) {
				for (const m of members) {
					if (m.userId !== myUserId) {
						await client.kick(roomId, m.userId, "Raum gelöscht").catch(() => {});
					}
				}
			}
			await client.leave(roomId);
			await client.forget(roomId).catch(() => {});
			onClose();
		} catch {
			toast.error("Raum konnte nicht verlassen werden.");
		} finally {
			setIsLeaving(false);
		}
	}, [client, roomId, onClose, members, myUserId, powerLevelsContent]);

	const displayName = room?.name ?? "";
	const initials = displayName.slice(0, 2).toUpperCase() || "?";
	const mxcAvatar = room?.getMxcAvatarUrl();
	const avatarSrc =
		avatarPreview ??
		(mxcAvatar ? `/api/matrix/media?mxc=${encodeURIComponent(mxcAvatar.slice(6))}` : undefined);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border bg-background overflow-hidden">
			<div className="flex items-center justify-between h-[57px] px-4 border-b border-border bg-background shrink-0">
				<span className="text-sm font-semibold">Raum Info</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<div className="flex-1 overflow-y-auto p-4 space-y-5">
				<div className="flex flex-col items-center text-center gap-2">
					<div className="relative">
						<Avatar className="h-[72px] w-[72px]">
							{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
							<AvatarFallback className="text-lg font-semibold bg-muted">{initials}</AvatarFallback>
						</Avatar>
						{canEditRoomInfo && (
							<button
								type="button"
								className="absolute bottom-0 right-0 h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
								title="Raum-Avatar ändern"
								onClick={() => avatarInputRef.current?.click()}
							>
								<Camera className="h-3.5 w-3.5" />
							</button>
						)}
						<input
							ref={avatarInputRef}
							type="file"
							accept="image/*"
							className="hidden"
							onChange={handleAvatarUpload}
						/>
					</div>
					<div className="w-full">
						{editingName ? (
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
								{canEditRoomInfo && (
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
						<p className="text-xs text-muted-foreground mt-0.5">{members.length} Mitglieder</p>
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

				{/* Stummschalten */}
				<button
					type="button"
					onClick={toggleMute}
					className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors"
				>
					{isMuted ? <BellOff className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
					{isMuted ? "Benachrichtigungen aktivieren" : "Stummschalten"}
				</button>

				{/* Thema */}
				<div>
					<div className="flex items-center gap-1 mb-1">
						<label className="text-xs font-medium text-muted-foreground">Thema</label>
						{!editingTopic && canEditRoomInfo && (
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
							className={
								canEditRoomInfo
									? "text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
									: "text-sm text-muted-foreground"
							}
							onClick={canEditRoomInfo ? () => setEditingTopic(true) : undefined}
						>
							{roomTopic || (canEditRoomInfo ? "Thema hinzufügen…" : "Kein Thema")}
						</p>
					)}
				</div>

				{/* Mitglieder */}
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
				{/* Invite-Link */}
				{(() => {
					const alias = room?.getCanonicalAlias();
					const link = alias ? `https://matrix.to/#/${alias}` : `https://matrix.to/#/${roomId}`;
					return (
						<div>
							<label className="text-xs font-medium text-muted-foreground mb-1 block">
								Einladungslink
							</label>
							<div className="flex items-center gap-2">
								<code className="flex-1 text-[10px] text-muted-foreground bg-muted/30 px-2 py-1 rounded truncate">
									{link}
								</code>
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 shrink-0"
									title="Kopieren"
									onClick={() => {
										navigator.clipboard.writeText(link);
										toast.success("Link kopiert");
									}}
								>
									<Copy className="h-3 w-3" />
								</Button>
							</div>
						</div>
					);
				})()}

				{/* Gepinnte Nachrichten */}
				{(() => {
					const pinnedEvent = room?.currentState.getStateEvents("m.room.pinned_events", "");
					const pinnedIds: string[] = pinnedEvent?.getContent()?.pinned ?? [];
					if (pinnedIds.length === 0) return null;
					const timeline = room?.getLiveTimeline().getEvents() ?? [];
					const pinnedMessages = pinnedIds
						.map((id) => timeline.find((ev) => ev.getId() === id))
						.filter(Boolean)
						.slice(0, 5);
					return (
						<div>
							<label className="text-xs font-medium text-muted-foreground mb-2 block">
								<Pin className="h-3 w-3 inline mr-1" />
								Angepinnt ({pinnedIds.length})
							</label>
							<div className="flex flex-col gap-1">
								{pinnedMessages.map((ev) => (
									<div
										key={ev!.getId()}
										className="text-xs text-muted-foreground bg-muted/30 rounded px-2 py-1.5 truncate"
									>
										<span className="font-medium">
											{ev!.getSender()?.split(":")[0]?.replace("@", "")}:
										</span>{" "}
										{(ev!.getContent()?.body as string)?.slice(0, 60) ?? "..."}
									</div>
								))}
								{pinnedIds.length > pinnedMessages.length && (
									<p className="text-[10px] text-muted-foreground">
										+{pinnedIds.length - pinnedMessages.length} weitere (nicht in Timeline)
									</p>
								)}
							</div>
						</div>
					);
				})()}

				{/* Geteilte Medien — Tabs mit Inhalten */}
				{(() => {
					if (!room) return null;
					const events = room
						.getLiveTimeline()
						.getEvents()
						.filter((ev) => ev.getType() === "m.room.message");
					const mediaItems = events.filter((ev) =>
						["m.image", "m.video"].includes(ev.getContent()?.msgtype as string),
					);
					const fileItems = events.filter((ev) =>
						["m.file", "m.audio"].includes(ev.getContent()?.msgtype as string),
					);
					const linkItems = events.filter((ev) =>
						(ev.getContent()?.body as string)?.match(/https?:\/\//),
					);
					if (mediaItems.length === 0 && fileItems.length === 0 && linkItems.length === 0)
						return null;
					return (
						<div>
							<label className="text-xs font-medium text-muted-foreground mb-2 block">
								Geteilte Medien
							</label>
							{mediaItems.length > 0 && (
								<div className="mb-2">
									<p className="text-[10px] text-muted-foreground mb-1">
										<Image className="h-3 w-3 inline mr-1" />
										Medien ({mediaItems.length})
									</p>
									<div className="flex flex-wrap gap-1">
										{mediaItems.slice(0, 6).map((ev) => {
											const url = ev.getContent()?.url as string;
											const src = url?.startsWith("mxc://")
												? `/api/matrix/media?mxc=${encodeURIComponent(url.slice(6))}&thumbnail=1&w=60&h=60`
												: undefined;
											return src ? (
												// biome-ignore lint/performance/noImgElement: Matrix-URLs dynamisch
												<img
													key={ev.getId()}
													src={src}
													alt=""
													className="h-12 w-12 rounded object-cover"
													loading="lazy"
												/>
											) : null;
										})}
										{mediaItems.length > 6 && (
											<p className="text-[10px] text-muted-foreground self-end">
												+{mediaItems.length - 6}
											</p>
										)}
									</div>
								</div>
							)}
							{fileItems.length > 0 && (
								<div className="mb-2">
									<p className="text-[10px] text-muted-foreground mb-1">
										<FileText className="h-3 w-3 inline mr-1" />
										Dateien ({fileItems.length})
									</p>
									{fileItems.slice(0, 3).map((ev) => (
										<p key={ev.getId()} className="text-[10px] text-muted-foreground truncate">
											{(ev.getContent()?.body as string) ?? "Datei"}
										</p>
									))}
								</div>
							)}
							{linkItems.length > 0 && (
								<div>
									<p className="text-[10px] text-muted-foreground mb-1">
										<Link2 className="h-3 w-3 inline mr-1" />
										Links ({linkItems.length})
									</p>
									{linkItems.slice(0, 3).map((ev) => {
										const body = ev.getContent()?.body as string;
										const match = body?.match(/https?:\/\/[^\s]+/);
										return match ? (
											<a
												key={ev.getId()}
												href={match[0]}
												target="_blank"
												rel="noopener noreferrer"
												className="text-[10px] text-primary truncate block hover:underline"
											>
												{match[0]}
											</a>
										) : null;
									})}
								</div>
							)}
						</div>
					);
				})()}

				{/* Rollen-Management (nur Admin) */}
				{myPowerLevel >= 100 && (
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
										<select
											value={member.powerLevel}
											onChange={(e) => {
												const level = Number.parseInt(e.target.value);
												client
													.setPowerLevel(roomId, member.userId, level)
													.catch(() => toast.error("Rolle ändern fehlgeschlagen"));
											}}
											className="text-[10px] bg-muted/30 border border-border/50 rounded px-1 py-0.5"
										>
											<option value={0}>Member</option>
											<option value={50}>Moderator</option>
											<option value={100}>Admin</option>
										</select>
									</div>
								))}
						</div>
					</div>
				)}

				{/* Gruppen-Einstellungen (nur Admin) */}
				{myPowerLevel >= 100 && (
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-2 block">
							<Shield className="h-3 w-3 inline mr-1" />
							Berechtigungen
						</label>
						<div className="space-y-2 text-xs">
							{[
								{
									key: "events_default",
									label: "Nachrichten senden",
									desc: "Wer darf Nachrichten senden",
								},
								{ key: "invite", label: "Einladen", desc: "Wer darf neue Mitglieder einladen" },
								{
									key: "state_default",
									label: "Raum-Info ändern",
									desc: "Wer darf Name/Topic/Avatar ändern",
								},
							].map(({ key, label }) => {
								const currentLevel =
									((powerLevelsContent ?? {}) as Record<string, number>)[key] ??
									(key === "state_default" ? 50 : 0);
								return (
									<div key={key} className="flex items-center justify-between">
										<span className="text-muted-foreground">{label}</span>
										<select
											value={currentLevel}
											onChange={(e) => {
												const level = Number.parseInt(e.target.value);
												const newPL = { ...(powerLevelsContent ?? {}), [key]: level };
												client
													.sendStateEvent(roomId, "m.room.power_levels" as any, newPL, "")
													.catch(() => toast.error("Berechtigung ändern fehlgeschlagen"));
											}}
											className="text-[10px] bg-muted/30 border border-border/50 rounded px-1 py-0.5"
										>
											<option value={0}>Alle</option>
											<option value={50}>Moderator+</option>
											<option value={100}>Admin</option>
										</select>
									</div>
								);
							})}
						</div>
					</div>
				)}
			</div>

			{/* Footer */}
			<div className="p-3 border-t border-border shrink-0">
				{membership === "invite" ? (
					<div className="flex gap-2">
						<Button
							className="flex-1 gap-1"
							onClick={() => {
								client
									.joinRoom(roomId)
									.then(() => toast.success("Beigetreten"))
									.catch(() => toast.error("Fehlgeschlagen"));
							}}
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
				) : leaveConfirm ? (
					<div className="flex items-center gap-2">
						<span className="text-xs text-muted-foreground flex-1">
							{myPowerLevel >= 100 ? "Raum wirklich löschen?" : "Raum wirklich verlassen?"}
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
						{myPowerLevel >= 100 ? "Raum löschen" : "Raum verlassen"}
					</Button>
				)}
			</div>
		</div>
	);
}
