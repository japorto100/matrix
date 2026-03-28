"use client";

import { Home } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { SpaceInfo } from "@/lib/matrix/hooks/useSpaces";
import { hashColor, mxcToHttp } from "@/lib/matrix/utils";
import { cn } from "@/lib/utils";
import { UserProfileDialog } from "./UserProfileDialog";

interface Props {
	spaces: SpaceInfo[];
	selectedSpaceId: string | null;
	onSelect: (spaceId: string | null) => void;
	client?: MatrixClient | null;
}

// Hash-basierte Farbe für Space-Avatare
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

export function SpaceSelector({ spaces, selectedSpaceId, onSelect, client }: Props) {
	const myUserId = client?.getUserId() ?? null;
	const myUser = myUserId ? client?.getUser(myUserId) : null;
	const myDisplayName = myUser?.displayName ?? myUserId ?? "";
	const myInitials = myDisplayName.slice(0, 2).toUpperCase() || "?";
	const myAvatarUrl = myUser?.avatarUrl?.startsWith("mxc://")
		? mxcToHttp(myUser.avatarUrl)
		: undefined;

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
			{spaces.length > 0 && <div className="w-6 h-px bg-border/50 my-0.5" />}

			{/* Space Icons */}
			{spaces.map((space) => {
				const isSelected = selectedSpaceId === space.roomId;
				const initials = space.name.slice(0, 2).toUpperCase();
				return (
					<Tooltip key={space.roomId}>
						<TooltipTrigger asChild>
							<button
								type="button"
								onClick={() => onSelect(space.roomId)}
								className={cn(
									"relative flex items-center justify-center h-10 w-10 rounded-xl transition-all",
									isSelected ? "rounded-2xl ring-2 ring-primary" : "hover:rounded-xl",
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
							</button>
						</TooltipTrigger>
						<TooltipContent side="right">{space.name} ({space.childRoomIds.length})</TooltipContent>
					</Tooltip>
				);
			})}

			{/* Spacer */}
			<div className="flex-1" />

			{/* Profil-Avatar (A4: aus Sidebar-Footer hierher) */}
			{client && (
				<Tooltip>
					<TooltipTrigger asChild>
						<div>
							<UserProfileDialog
								client={client}
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
		</TooltipProvider>
	);
}
