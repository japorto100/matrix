"use client";

// KGNodeBase — Shared base for all 6 KG node component types
// Provides handle wiring + click area + selected state. Each node type wraps this.

import { Handle, Position } from "@xyflow/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { KGNodeType } from "../types";
import { NODE_TYPE_COLORS } from "../types";

interface KGNodeBaseProps {
	nodeType: KGNodeType;
	label: string;
	subtitle?: string;
	icon: ReactNode;
	confidence?: number;
	selected?: boolean;
	shape?: "rect" | "rounded" | "circle" | "hexagon" | "diamond" | "star";
}

export function KGNodeBase({
	nodeType,
	label,
	subtitle,
	icon,
	confidence,
	selected = false,
	shape = "rounded",
}: KGNodeBaseProps) {
	const color = NODE_TYPE_COLORS[nodeType];

	const shapeClass = {
		rect: "rounded-md",
		rounded: "rounded-xl",
		circle: "rounded-full",
		hexagon: "rounded-2xl",
		diamond: "rounded-md rotate-45",
		star: "rounded-lg",
	}[shape];

	const labelRotateClass = shape === "diamond" ? "-rotate-45" : "";

	return (
		<div className="relative">
			<Handle
				type="target"
				position={Position.Top}
				className="!bg-transparent !border-0 !w-2 !h-2"
			/>
			<div
				className={cn(
					"flex items-center gap-2 px-3 py-2 min-w-[140px]",
					"border-2 transition-all backdrop-blur-sm",
					shapeClass,
					selected ? "shadow-lg scale-105" : "shadow-md",
				)}
				style={{
					backgroundColor: `${color}20`,
					borderColor: selected ? color : `${color}80`,
					boxShadow: selected ? `0 0 0 2px ${color}60, 0 4px 14px ${color}30` : undefined,
				}}
			>
				<div className={cn("flex items-center gap-2", labelRotateClass)}>
					<div className="rounded-md p-1 shrink-0" style={{ backgroundColor: `${color}40` }}>
						{icon}
					</div>
					<div className="min-w-0">
						<div className="text-[11px] font-bold leading-tight truncate" style={{ color }}>
							{label}
						</div>
						{subtitle && (
							<div className="text-[9px] text-muted-foreground truncate font-mono">{subtitle}</div>
						)}
					</div>
					{confidence !== undefined && (
						<div className="ml-auto text-[9px] font-mono shrink-0 text-muted-foreground">
							{Math.round(confidence * 100)}%
						</div>
					)}
				</div>
			</div>
			<Handle
				type="source"
				position={Position.Bottom}
				className="!bg-transparent !border-0 !w-2 !h-2"
			/>
		</div>
	);
}
