"use client";

// 6 Custom Node Components for react-flow — one per KG node type.
// Each maps a different shape, icon, and color from NODE_TYPE_COLORS.

import type { NodeProps } from "@xyflow/react";
import { Activity, Building2, Coins, Radio, Sparkles, Zap } from "lucide-react";
import type { KGNodeProperties, KGNodeType } from "../types";
import { KGNodeBase } from "./KGNodeBase";

// react-flow's Node data shape we use throughout
export interface TradingKGNodeData extends Record<string, unknown> {
	nodeType: KGNodeType;
	label: string;
	properties: KGNodeProperties;
	confidence: number;
}

function pickSubtitle(properties: KGNodeProperties): string | undefined {
	const keys = Object.keys(properties);
	if (keys.length === 0) return undefined;
	const first = keys[0]!;
	const value = properties[first];
	return `${first}: ${value}`;
}

export function StratagemNode({ data, selected }: NodeProps & { data: TradingKGNodeData }) {
	return (
		<KGNodeBase
			nodeType="Stratagem"
			label={data.label}
			subtitle={pickSubtitle(data.properties)}
			icon={<Sparkles className="h-3 w-3 text-foreground" />}
			confidence={data.confidence}
			selected={selected}
			shape="rect"
		/>
	);
}

export function RegimeNode({ data, selected }: NodeProps & { data: TradingKGNodeData }) {
	return (
		<KGNodeBase
			nodeType="Regime"
			label={data.label}
			subtitle={pickSubtitle(data.properties)}
			icon={<Activity className="h-3 w-3 text-foreground" />}
			confidence={data.confidence}
			selected={selected}
			shape="hexagon"
		/>
	);
}

export function TransmissionChannelNode({
	data,
	selected,
}: NodeProps & { data: TradingKGNodeData }) {
	return (
		<KGNodeBase
			nodeType="TransmissionChannel"
			label={data.label}
			subtitle={pickSubtitle(data.properties)}
			icon={<Radio className="h-3 w-3 text-foreground" />}
			confidence={data.confidence}
			selected={selected}
			shape="circle"
		/>
	);
}

export function AssetNode({ data, selected }: NodeProps & { data: TradingKGNodeData }) {
	return (
		<KGNodeBase
			nodeType="Asset"
			label={data.label}
			subtitle={pickSubtitle(data.properties)}
			icon={<Coins className="h-3 w-3 text-foreground" />}
			confidence={data.confidence}
			selected={selected}
			shape="rounded"
		/>
	);
}

export function InstitutionNode({ data, selected }: NodeProps & { data: TradingKGNodeData }) {
	return (
		<KGNodeBase
			nodeType="Institution"
			label={data.label}
			subtitle={pickSubtitle(data.properties)}
			icon={<Building2 className="h-3 w-3 text-foreground" />}
			confidence={data.confidence}
			selected={selected}
			shape="rect"
		/>
	);
}

export function BTEMarkerNode({ data, selected }: NodeProps & { data: TradingKGNodeData }) {
	return (
		<KGNodeBase
			nodeType="BTEMarker"
			label={data.label}
			subtitle={pickSubtitle(data.properties)}
			icon={<Zap className="h-3 w-3 text-foreground" />}
			confidence={data.confidence}
			selected={selected}
			shape="star"
		/>
	);
}

// Map node type → component for react-flow's nodeTypes prop
export const TRADING_KG_NODE_TYPES = {
	Stratagem: StratagemNode,
	Regime: RegimeNode,
	TransmissionChannel: TransmissionChannelNode,
	Asset: AssetNode,
	Institution: InstitutionNode,
	BTEMarker: BTEMarkerNode,
} as const;
