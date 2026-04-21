"use client";

import { dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
	label: string;
	count: number;
	collapsed: boolean;
	onToggle: () => void;
	highlightAmber?: boolean;
	subLabel?: string;
	/** Lobby-DnD: bei gesetztem groupId wird der Header als drop-target registriert. */
	groupId?: string;
}

/**
 * N3: Collapsible Group-Header fuer die RoomList-Categories.
 * Lobby-DnD: optional drop-target fuer Room-Items (Tag-Mutation wird in
 * RoomList.tsx via monitorForElements gehandhabt).
 */
export function RoomGroupHeader({
	label,
	count,
	collapsed,
	onToggle,
	highlightAmber,
	subLabel,
	groupId,
}: Props) {
	const ref = useRef<HTMLButtonElement>(null);
	const [isDropping, setIsDropping] = useState(false);

	useEffect(() => {
		const el = ref.current;
		if (!el || !groupId) return;
		return dropTargetForElements({
			element: el,
			canDrop: ({ source }) => {
				const data = source.data;
				return data.type === "matrix.room-item" && typeof data.roomId === "string";
			},
			getData: () => ({ type: "matrix.room-group", groupId }),
			onDragEnter: () => setIsDropping(true),
			onDragLeave: () => setIsDropping(false),
			onDrop: () => setIsDropping(false),
		});
	}, [groupId]);

	return (
		<button
			ref={ref}
			type="button"
			onClick={onToggle}
			aria-expanded={!collapsed}
			className={cn(
				"w-full flex items-center gap-1.5 px-2 py-1 hover:bg-muted/30 transition-colors",
				highlightAmber && "text-primary",
				isDropping && "bg-primary/15 ring-1 ring-primary rounded",
			)}
		>
			{collapsed ? (
				<ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
			) : (
				<ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
			)}
			<span
				className={cn(
					"text-[10px] font-semibold uppercase tracking-wider",
					highlightAmber ? "text-primary" : "text-muted-foreground",
				)}
			>
				{label}
			</span>
			{subLabel && (
				<span className="text-[10px] text-muted-foreground/70 truncate">· {subLabel}</span>
			)}
			<span className="ml-auto text-[10px] text-muted-foreground tabular-nums">{count}</span>
		</button>
	);
}
