"use client";

import type { SpaceChildRoom, SpaceInfo } from "@matrix/lib/hooks/useSpaces";
import { hashColor, mxcToHttp } from "@matrix/lib/utils";
import { ChevronDown, ChevronUp, Folder, Hash, Sparkles, UserPlus, Users } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { InviteUsersToSpaceDialog } from "./InviteUsersToSpaceDialog";

interface Props {
	client: MatrixClient;
	space: SpaceInfo;
	hierarchy?: SpaceChildRoom[];
	onFetchHierarchy: () => void;
	onSelectRoom: (roomId: string) => void;
}

const HIERARCHY_COLLAPSED_ROWS = 5;
const SPACE_COLORS = [
	"bg-blue-600",
	"bg-emerald-600",
	"bg-violet-600",
	"bg-amber-600",
	"bg-rose-600",
	"bg-cyan-600",
	"bg-indigo-600",
	"bg-pink-600",
];

function getExpandedStorageKey(spaceId: string) {
	return `matrix.lobby.${spaceId}.expanded`;
}

/**
 * E1 Space-Lobby-View — eingebettet oberhalb der RoomList.
 *
 * Default-State: **collapsed** fuer Neukunden (Contrarian-Amendment #3). User
 * sieht die normale RoomList sofort; kann die Lobby per Toggle aufklappen.
 * Innerhalb: Hero (Name, Topic, Member-Count, Invite-Button) + Hierarchy-List
 * mit max 5 Rows (+ "Alle anzeigen"-Expand bei mehr).
 *
 * Gating: Lobby wird nur gerendert wenn der Space childRoomIds hat oder
 * Hierarchy-Daten existieren (sonst ist's leeres UI).
 */
export function SpaceLobby({ client, space, hierarchy, onFetchHierarchy, onSelectRoom }: Props) {
	const [expanded, setExpanded] = useState<boolean>(() => {
		if (typeof window === "undefined") return false;
		return localStorage.getItem(getExpandedStorageKey(space.roomId)) === "true";
	});
	const [showAllRows, setShowAllRows] = useState(false);
	const [inviteOpen, setInviteOpen] = useState(false);

	useEffect(() => {
		localStorage.setItem(getExpandedStorageKey(space.roomId), String(expanded));
	}, [space.roomId, expanded]);

	useEffect(() => {
		if (expanded && !hierarchy) onFetchHierarchy();
	}, [expanded, hierarchy, onFetchHierarchy]);

	const room = client.getRoom(space.roomId);
	const topic =
		(room?.currentState.getStateEvents("m.room.topic", "")?.getContent()?.topic as
			| string
			| undefined) ?? "";
	const memberCount = room?.getInvitedAndJoinedMemberCount() ?? 0;
	const mxcAvatar = room?.getMxcAvatarUrl();
	const avatarSrc = mxcAvatar ? mxcToHttp(mxcAvatar) : undefined;
	const initials = space.name.slice(0, 2).toUpperCase();
	const bgColor = hashColor(space.name, SPACE_COLORS);

	const visibleChildren = useMemo(() => {
		if (!hierarchy) return [];
		if (showAllRows) return hierarchy;
		return hierarchy.slice(0, HIERARCHY_COLLAPSED_ROWS);
	}, [hierarchy, showAllRows]);

	// Nichts zu rendern wenn Space leer + collapsed — dann verbergen.
	if (space.childRoomIds.length === 0 && !expanded) return null;

	return (
		<>
			<div className="border-b border-border/50 bg-muted/20">
				<button
					type="button"
					onClick={() => setExpanded((v) => !v)}
					className="w-full flex items-center gap-3 px-3 py-2 hover:bg-muted/30 transition-colors"
				>
					<Avatar className="h-8 w-8 shrink-0">
						{avatarSrc && <AvatarImage src={avatarSrc} alt={space.name} />}
						<AvatarFallback className={cn("text-[10px] font-semibold text-white", bgColor)}>
							{initials}
						</AvatarFallback>
					</Avatar>
					<div className="flex-1 min-w-0 text-left">
						<div className="text-sm font-semibold truncate">{space.name}</div>
						<div className="text-[10px] text-muted-foreground">
							{memberCount} Mitglieder · {space.childRoomIds.length} Räume
						</div>
					</div>
					{expanded ? (
						<ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
					) : (
						<ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
					)}
				</button>

				{expanded && (
					<div className="px-3 pb-3 space-y-3">
						{/* Hero: Topic + Actions */}
						{topic && <p className="text-xs text-muted-foreground line-clamp-2">{topic}</p>}
						<Button
							variant="outline"
							size="sm"
							className="w-full h-7 text-xs"
							onClick={() => setInviteOpen(true)}
						>
							<UserPlus className="h-3 w-3 mr-1.5" />
							Personen einladen
						</Button>

						{/* Hierarchy-List */}
						<div className="flex flex-col gap-1">
							<div className="flex items-center justify-between px-1">
								<label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
									Hierarchie
								</label>
								{hierarchy && hierarchy.length > HIERARCHY_COLLAPSED_ROWS && (
									<button
										type="button"
										onClick={() => setShowAllRows((v) => !v)}
										className="text-[10px] text-primary hover:underline"
									>
										{showAllRows ? "Weniger" : `Alle ${hierarchy.length} anzeigen`}
									</button>
								)}
							</div>

							{!hierarchy ? (
								<p className="text-[10px] text-muted-foreground py-2">Lade Hierarchie…</p>
							) : visibleChildren.length === 0 ? (
								<p className="text-[10px] text-muted-foreground py-2">Keine Raeume im Space.</p>
							) : (
								visibleChildren.map((child) => (
									<LobbyRow
										key={child.roomId}
										child={child}
										client={client}
										onSelect={onSelectRoom}
										onRefresh={onFetchHierarchy}
									/>
								))
							)}
						</div>
					</div>
				)}
			</div>

			{inviteOpen && (
				<InviteUsersToSpaceDialog
					client={client}
					roomId={space.roomId}
					roomName={space.name}
					open={inviteOpen}
					onOpenChange={setInviteOpen}
				/>
			)}
		</>
	);
}

interface LobbyRowProps {
	child: SpaceChildRoom;
	client: MatrixClient;
	onSelect: (roomId: string) => void;
	onRefresh: () => void;
}

function LobbyRow({ child, client, onSelect, onRefresh }: LobbyRowProps) {
	const [joining, setJoining] = useState(false);
	const Icon = child.isSpace ? Folder : Hash;
	const avatarSrc = child.avatarUrl?.startsWith("mxc://") ? mxcToHttp(child.avatarUrl) : undefined;

	const handleJoin = async () => {
		setJoining(true);
		try {
			await client.joinRoom(child.roomId);
			toast.success(`Beigetreten: ${child.name}`);
			onRefresh();
			onSelect(child.roomId);
		} catch {
			toast.error("Beitreten fehlgeschlagen.");
		} finally {
			setJoining(false);
		}
	};

	return (
		<div
			className={cn(
				"flex items-center gap-2 px-1.5 py-1 rounded hover:bg-muted/50 group",
				child.suggested && "bg-amber-500/5 hover:bg-amber-500/10",
			)}
		>
			<div className="shrink-0">
				{avatarSrc ? (
					<Avatar className="h-5 w-5">
						<AvatarImage src={avatarSrc} alt={child.name} />
						<AvatarFallback className="text-[9px] bg-muted">
							<Icon className="h-3 w-3" />
						</AvatarFallback>
					</Avatar>
				) : (
					<div className="h-5 w-5 rounded bg-muted flex items-center justify-center">
						<Icon className="h-3 w-3 text-muted-foreground" />
					</div>
				)}
			</div>
			<div className="flex-1 min-w-0">
				<div className="flex items-center gap-1">
					<span className="text-xs font-medium truncate">{child.name}</span>
					{child.suggested && (
						<Sparkles className="h-2.5 w-2.5 text-amber-500 shrink-0" aria-label="Empfohlen" />
					)}
				</div>
				<div className="flex items-center gap-1 text-[10px] text-muted-foreground">
					<Users className="h-2.5 w-2.5" />
					{child.memberCount}
					{child.isSpace && " · Space"}
				</div>
			</div>
			{child.isJoined ? (
				<Button
					variant="ghost"
					size="sm"
					className="h-6 text-[10px] opacity-0 group-hover:opacity-100"
					onClick={() => onSelect(child.roomId)}
				>
					Öffnen
				</Button>
			) : (
				<Button
					variant="outline"
					size="sm"
					className="h-6 text-[10px]"
					onClick={() => void handleJoin()}
					disabled={joining}
				>
					{joining ? "…" : "Beitreten"}
				</Button>
			)}
		</div>
	);
}
