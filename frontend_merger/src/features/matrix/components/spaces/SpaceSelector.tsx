"use client";

import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import {
	draggable,
	dropTargetForElements,
	monitorForElements,
} from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import {
	attachClosestEdge,
	type Edge,
	extractClosestEdge,
} from "@atlaskit/pragmatic-drag-and-drop-hitbox/closest-edge";
import { useSpaceOrder } from "@matrix/lib/hooks/useSpaceOrder";
import type { SpaceInfo } from "@matrix/lib/hooks/useSpaces";
import { hashColor, mxcToHttp } from "@matrix/lib/utils";
import { Bell, Home, Plus } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { AppSettingsSheet } from "../AppSettingsSheet";
import { UserProfileDialog } from "../UserProfileDialog";
import { CreateSpaceDialog } from "./CreateSpaceDialog";

interface Props {
	spaces: SpaceInfo[];
	selectedSpaceId: string | null;
	onSelect: (spaceId: string | null) => void;
	onActivityOpen?: () => void;
	onSpaceSettings?: (spaceId: string) => void;
	activityCount?: number;
	/** Map spaceId → aggregierter Unread-Count der Child-Rooms. */
	spaceUnread?: Record<string, number>;
	client?: MatrixClient | null;
}

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
const spaceColor = (name: string) => hashColor(name, SPACE_COLORS);

const DND_ITEM_TYPE = "matrix.space-icon";
const LOCAL_ONLY_TOAST_KEY = "matrix.spaceOrderToastShown";

type SpaceDragData = {
	type: typeof DND_ITEM_TYPE;
	spaceId: string;
};

function isSpaceDragData(data: Record<string | symbol, unknown>): data is SpaceDragData {
	return data.type === DND_ITEM_TYPE && typeof data.spaceId === "string";
}

export function SpaceSelector({
	spaces,
	selectedSpaceId,
	onSelect,
	onActivityOpen,
	onSpaceSettings,
	activityCount,
	spaceUnread,
	client,
}: Props) {
	const [showCreateSpace, setShowCreateSpace] = useState(false);
	const [showAppSettings, setShowAppSettings] = useState(false);
	const { sortSpaces, moveSpace } = useSpaceOrder();
	const orderedSpaces = useMemo(() => sortSpaces(spaces), [spaces, sortSpaces]);
	const knownIds = useMemo(() => orderedSpaces.map((s) => s.roomId), [orderedSpaces]);

	const myUserId = client?.getUserId() ?? null;
	const myUser = myUserId ? client?.getUser(myUserId) : null;
	const myDisplayName = myUser?.displayName ?? myUserId ?? "";
	const myInitials = myDisplayName.slice(0, 2).toUpperCase() || "?";
	const myAvatarUrl = myUser?.avatarUrl?.startsWith("mxc://")
		? mxcToHttp(myUser.avatarUrl)
		: undefined;

	// N5: Monitor fuer drop-handling. Registriert einmal, reagiert auf alle Space-Drags.
	useEffect(() => {
		return monitorForElements({
			canMonitor: ({ source }) => isSpaceDragData(source.data),
			onDrop: ({ source, location }) => {
				const sourceData = source.data;
				if (!isSpaceDragData(sourceData)) return;
				const target = location.current.dropTargets[0];
				if (!target) return;
				const targetData = target.data;
				if (!isSpaceDragData(targetData)) return;
				if (sourceData.spaceId === targetData.spaceId) return;
				const edge = extractClosestEdge(targetData);
				const before = edge === "top" || edge === "left";
				moveSpace(sourceData.spaceId, targetData.spaceId, before, knownIds);
				if (typeof window !== "undefined" && !localStorage.getItem(LOCAL_ONLY_TOAST_KEY)) {
					toast.info("Reihenfolge nur auf diesem Gerät gespeichert.");
					localStorage.setItem(LOCAL_ONLY_TOAST_KEY, "true");
				}
			},
		});
	}, [moveSpace, knownIds]);

	return (
		<TooltipProvider delayDuration={300}>
			<div className="w-14 shrink-0 flex flex-col items-center py-2 gap-1.5 border-r border-border/50 bg-sidebar overflow-y-auto scrollbar-hide">
				{/* Home — Alle Räume */}
				<Tooltip>
					<TooltipTrigger asChild>
						<button
							type="button"
							onClick={() => onSelect(null)}
							className={cn(
								"relative flex items-center justify-center h-10 w-10 rounded-xl transition-all",
								selectedSpaceId === null
									? "bg-primary text-primary-foreground rounded-2xl"
									: "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground hover:rounded-xl",
							)}
						>
							<Home className="h-5 w-5" />
							{selectedSpaceId === null && (
								<span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r bg-primary" />
							)}
						</button>
					</TooltipTrigger>
					<TooltipContent side="right">Alle Chats</TooltipContent>
				</Tooltip>

				{/* Separator */}
				{orderedSpaces.length > 0 && <div className="w-6 h-px bg-border/50 my-0.5" />}

				{/* Space Icons */}
				{orderedSpaces.map((space) => {
					const isSelected = selectedSpaceId === space.roomId;
					const unread = spaceUnread?.[space.roomId] ?? 0;
					return (
						<DraggableSpaceItem
							key={space.roomId}
							space={space}
							isSelected={isSelected}
							unread={unread}
							onSelect={() => onSelect(space.roomId)}
							onSettings={() => onSpaceSettings?.(space.roomId)}
						/>
					);
				})}

				{/* Space erstellen */}
				{client && (
					<Tooltip>
						<TooltipTrigger asChild>
							<button
								type="button"
								onClick={() => setShowCreateSpace(true)}
								className="flex items-center justify-center h-10 w-10 rounded-xl bg-muted/30 text-muted-foreground hover:bg-muted hover:text-foreground hover:rounded-2xl transition-all"
							>
								<Plus className="h-5 w-5" />
							</button>
						</TooltipTrigger>
						<TooltipContent side="right">Space erstellen</TooltipContent>
					</Tooltip>
				)}

				{/* Activity Centre */}
				{onActivityOpen && (
					<Tooltip>
						<TooltipTrigger asChild>
							<button
								type="button"
								onClick={onActivityOpen}
								className="relative flex items-center justify-center h-10 w-10 rounded-xl bg-muted/30 text-muted-foreground hover:bg-muted hover:text-foreground hover:rounded-2xl transition-all"
							>
								<Bell className="h-5 w-5" />
								{(activityCount ?? 0) > 0 && (
									<span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-destructive text-destructive-foreground text-[9px] font-semibold">
										{activityCount! > 99 ? "99+" : activityCount}
									</span>
								)}
							</button>
						</TooltipTrigger>
						<TooltipContent side="right">Aktivität</TooltipContent>
					</Tooltip>
				)}

				{/* Spacer */}
				<div className="flex-1" />

				{/* Profil-Avatar */}
				{client && (
					<Tooltip>
						<TooltipTrigger asChild>
							<div>
								<UserProfileDialog
									client={client}
									onOpenSettings={() => setShowAppSettings(true)}
									trigger={
										<button
											type="button"
											className="flex items-center justify-center h-10 w-10 rounded-xl hover:rounded-2xl transition-all"
										>
											<Avatar className="h-9 w-9">
												{myAvatarUrl && <AvatarImage src={myAvatarUrl} />}
												<AvatarFallback className="text-[10px] bg-muted text-muted-foreground">
													{myInitials}
												</AvatarFallback>
											</Avatar>
										</button>
									}
								/>
							</div>
						</TooltipTrigger>
						<TooltipContent side="right">{myDisplayName}</TooltipContent>
					</Tooltip>
				)}
			</div>

			{/* CreateSpaceDialog */}
			{client && showCreateSpace && (
				<CreateSpaceDialog
					client={client}
					open={showCreateSpace}
					onOpenChange={setShowCreateSpace}
				/>
			)}

			{/* AppSettingsSheet — triggered via UserProfileDialog "Einstellungen"-Link */}
			{client && (
				<AppSettingsSheet
					client={client}
					open={showAppSettings}
					onOpenChange={setShowAppSettings}
				/>
			)}
		</TooltipProvider>
	);
}

interface DraggableSpaceItemProps {
	space: SpaceInfo;
	isSelected: boolean;
	unread: number;
	onSelect: () => void;
	onSettings: () => void;
}

function DraggableSpaceItem({
	space,
	isSelected,
	unread,
	onSelect,
	onSettings,
}: DraggableSpaceItemProps) {
	const ref = useRef<HTMLButtonElement>(null);
	const [dragging, setDragging] = useState(false);
	const [closestEdge, setClosestEdge] = useState<Edge | null>(null);
	const initials = space.name.slice(0, 2).toUpperCase();

	useEffect(() => {
		const el = ref.current;
		if (!el) return;
		const data: SpaceDragData = { type: DND_ITEM_TYPE, spaceId: space.roomId };
		return combine(
			draggable({
				element: el,
				getInitialData: () => data,
				onDragStart: () => setDragging(true),
				onDrop: () => setDragging(false),
			}),
			dropTargetForElements({
				element: el,
				canDrop: ({ source }) =>
					isSpaceDragData(source.data) && source.data.spaceId !== space.roomId,
				getData: ({ input, element }) =>
					attachClosestEdge(data, { element, input, allowedEdges: ["top", "bottom"] }),
				onDrag: ({ self, source }) => {
					if (!isSpaceDragData(source.data) || source.data.spaceId === space.roomId) {
						setClosestEdge(null);
						return;
					}
					setClosestEdge(extractClosestEdge(self.data));
				},
				onDragLeave: () => setClosestEdge(null),
				onDrop: () => setClosestEdge(null),
			}),
		);
	}, [space.roomId]);

	return (
		<Tooltip>
			<TooltipTrigger asChild>
				<button
					ref={ref}
					type="button"
					onClick={onSelect}
					onContextMenu={(e) => {
						e.preventDefault();
						onSettings();
					}}
					aria-grabbed={dragging}
					className={cn(
						"relative flex items-center justify-center h-10 w-10 rounded-xl transition-all",
						isSelected ? "rounded-2xl ring-2 ring-primary" : "hover:rounded-xl",
						dragging && "opacity-40",
					)}
				>
					<Avatar className="h-10 w-10">
						<AvatarFallback
							className={cn(
								"text-xs font-semibold text-white rounded-xl",
								isSelected ? "rounded-2xl" : "",
								spaceColor(space.name),
							)}
						>
							{initials}
						</AvatarFallback>
					</Avatar>
					{isSelected && (
						<span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r bg-primary" />
					)}
					{unread > 0 && (
						<span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-destructive text-destructive-foreground text-[9px] font-semibold">
							{unread > 99 ? "99+" : unread}
						</span>
					)}
					{closestEdge === "top" && (
						<span className="absolute -top-[3px] left-0 right-0 h-[2px] bg-primary rounded-full" />
					)}
					{closestEdge === "bottom" && (
						<span className="absolute -bottom-[3px] left-0 right-0 h-[2px] bg-primary rounded-full" />
					)}
				</button>
			</TooltipTrigger>
			<TooltipContent side="right">
				{space.name} ({space.childRoomIds.length}
				{unread > 0 ? ` · ${unread} ungelesen` : ""})
			</TooltipContent>
		</Tooltip>
	);
}
