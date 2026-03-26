"use client";

import { ChevronDown, Layers } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { SpaceInfo } from "@/lib/matrix/hooks/useSpaces";
import { cn } from "@/lib/utils";

interface Props {
	spaces: SpaceInfo[];
	selectedSpaceId: string | null;
	onSelect: (spaceId: string | null) => void;
}

export function SpaceSelector({ spaces, selectedSpaceId, onSelect }: Props) {
	const [open, setOpen] = useState(false);
	const ref = useRef<HTMLDivElement>(null);

	// Click-Outside schließt das Dropdown
	useEffect(() => {
		if (!open) return;
		function handleClick(e: MouseEvent) {
			if (ref.current && !ref.current.contains(e.target as Node)) {
				setOpen(false);
			}
		}
		document.addEventListener("mousedown", handleClick);
		return () => document.removeEventListener("mousedown", handleClick);
	}, [open]);

	if (spaces.length === 0) return null;

	const selectedSpace = spaces.find((s) => s.roomId === selectedSpaceId);
	const label = selectedSpace?.name ?? "Alle Räume";

	return (
		<div className="relative px-3 pt-2 pb-1" ref={ref}>
			<button
				type="button"
				onClick={() => setOpen((v) => !v)}
				className={cn(
					"w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs font-medium",
					"hover:bg-accent hover:text-accent-foreground transition-colors",
					"border border-border bg-background",
				)}
			>
				<Layers className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
				<span className="truncate flex-1 text-left">{label}</span>
				<ChevronDown
					className={cn(
						"h-3 w-3 shrink-0 text-muted-foreground transition-transform",
						open && "rotate-180",
					)}
				/>
			</button>
			{open && (
				<div className="absolute left-3 right-3 top-full mt-1 z-20 bg-popover border rounded-md shadow-lg py-1 max-h-48 overflow-y-auto">
					<button
						type="button"
						onClick={() => {
							onSelect(null);
							setOpen(false);
						}}
						className={cn(
							"w-full text-left px-3 py-1.5 text-xs hover:bg-accent transition-colors",
							!selectedSpaceId && "font-semibold text-primary",
						)}
					>
						Alle Räume
					</button>
					{spaces.map((space) => (
						<button
							key={space.roomId}
							type="button"
							onClick={() => {
								onSelect(space.roomId);
								setOpen(false);
							}}
							className={cn(
								"w-full text-left px-3 py-1.5 text-xs hover:bg-accent transition-colors truncate",
								selectedSpaceId === space.roomId && "font-semibold text-primary",
							)}
						>
							{space.name}
							<span className="text-muted-foreground ml-1">({space.childRoomIds.length})</span>
						</button>
					))}
				</div>
			)}
		</div>
	);
}
