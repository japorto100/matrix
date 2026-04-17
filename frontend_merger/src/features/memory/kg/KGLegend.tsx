"use client";

// KGLegend — Shows the 6 node types + 6 edge types with colors
// Pinned to bottom-right corner of the KG graph.

import { Activity, Building2, Coins, Radio, Sparkles, Zap } from "lucide-react";
import {
	EDGE_TYPE_COLORS,
	getEdgeTypeLabel,
	getNodeTypeLabel,
	type KGEdgeType,
	type KGNodeType,
	NODE_TYPE_COLORS,
} from "./types";

const NODE_ICON: Record<KGNodeType, typeof Sparkles> = {
	Stratagem: Sparkles,
	Regime: Activity,
	TransmissionChannel: Radio,
	Asset: Coins,
	Institution: Building2,
	BTEMarker: Zap,
};

const NODE_TYPES: KGNodeType[] = [
	"Stratagem",
	"Regime",
	"TransmissionChannel",
	"Asset",
	"Institution",
	"BTEMarker",
];

const EDGE_TYPES: KGEdgeType[] = [
	"causes",
	"inhibits",
	"activates",
	"precedes",
	"transmits",
	"signals",
];

export function KGLegend() {
	return (
		<div className="absolute bottom-4 left-4 z-10 bg-card/95 backdrop-blur border border-border rounded-lg p-3 shadow-lg max-w-[260px]">
			<div className="space-y-3">
				<div>
					<p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/80 mb-1.5">
						Node Types
					</p>
					<div className="grid grid-cols-2 gap-1.5">
						{NODE_TYPES.map((type) => {
							const Icon = NODE_ICON[type];
							const color = NODE_TYPE_COLORS[type];
							return (
								<div key={type} className="flex items-center gap-1.5">
									<div className="rounded p-0.5 shrink-0" style={{ backgroundColor: `${color}30` }}>
										<Icon className="h-2.5 w-2.5" style={{ color }} />
									</div>
									<span className="text-[10px] font-medium">{getNodeTypeLabel(type)}</span>
								</div>
							);
						})}
					</div>
				</div>

				<div className="border-t border-border/50 pt-2">
					<p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/80 mb-1.5">
						Edge Types
					</p>
					<div className="grid grid-cols-2 gap-1">
						{EDGE_TYPES.map((edgeType) => {
							const color = EDGE_TYPE_COLORS[edgeType];
							return (
								<div key={edgeType} className="flex items-center gap-1.5">
									<svg width="16" height="6" viewBox="0 0 16 6">
										<title>{edgeType}</title>
										<line
											x1="0"
											y1="3"
											x2="16"
											y2="3"
											stroke={color}
											strokeWidth="2"
											strokeDasharray={
												edgeType === "inhibits"
													? "3 2"
													: edgeType === "activates"
														? "1 2"
														: undefined
											}
										/>
									</svg>
									<span className="text-[10px] font-mono">{getEdgeTypeLabel(edgeType)}</span>
								</div>
							);
						})}
					</div>
				</div>
			</div>
		</div>
	);
}
