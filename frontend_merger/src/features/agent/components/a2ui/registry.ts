/**
 * Generative-UI Widget Registry (ex-Tambo → A2UI v0.9 target)
 *
 * Tambo-provider entfernt 2026-04-21. Die Widgets (ChartWidget, PortfolioCard)
 * bleiben als normale React-components und werden via A2UI renderer
 * gemountet sobald python-agent A2UI-widget-messages streamed (Google Spec v0.9).
 *
 * A2UI mapping: name = A2UI widget-type-id. propsSchema bleibt als A2UI-
 * data-contract identisch (JSON-Schema ist A2UI-konform).
 *
 * Migration-Status: schemas sind Tambo-compatible, brauchen A2UI-wrapper
 * (WidgetDefinition) wenn A2UI-Renderer aktiv wird — siehe exec-09 §A2UI.
 */

import type { ComponentType } from "react";
import { ChartWidget } from "./ChartWidget";
import { PortfolioCard } from "./PortfolioCard";

export interface GenerativeWidget {
	/** Widget type-id (matches A2UI widget.type) */
	name: string;
	/** Human-readable description (agent uses for widget selection) */
	description: string;
	/** React component */
	// biome-ignore lint/suspicious/noExplicitAny: widget props vary per type
	component: ComponentType<any>;
	/** JSON-Schema for props (A2UI data-contract) */
	propsSchema: Record<string, unknown>;
}

export const generativeWidgets: GenerativeWidget[] = [
	{
		name: "ChartWidget",
		description: "Zeigt einen Trading-Chart mit Symbol, Timeframe, Preis und Indikatoren.",
		component: ChartWidget,
		propsSchema: {
			type: "object",
			properties: {
				symbol: { type: "string", description: "Trading symbol (e.g. EUR/USD)" },
				timeframe: { type: "string", description: "Chart timeframe (1m, 5m, 1H, 4H, 1D)" },
				indicators: { type: "array", items: { type: "string" }, description: "Active indicators" },
				price: { type: "number", description: "Current price" },
				change24h: { type: "number", description: "24h change percentage" },
			},
			required: ["symbol", "timeframe"],
		},
	},
	{
		name: "PortfolioCard",
		description: "Zeigt eine Portfolio-Übersicht mit Positionen und P&L.",
		component: PortfolioCard,
		propsSchema: {
			type: "object",
			properties: {
				totalValue: { type: "number", description: "Total portfolio value in USD" },
				positions: {
					type: "array",
					items: {
						type: "object",
						properties: {
							symbol: { type: "string" },
							size: { type: "number" },
							entryPrice: { type: "number" },
							currentPrice: { type: "number" },
							pnl: { type: "number" },
						},
						required: ["symbol", "size", "entryPrice", "currentPrice", "pnl"],
					},
				},
				dayPnl: { type: "number", description: "Today's P&L" },
			},
			required: ["totalValue", "positions"],
		},
	},
];

/**
 * Lookup widget by name. Used by A2UI renderer to resolve widget.type → component.
 */
export function getGenerativeWidget(name: string): GenerativeWidget | undefined {
	return generativeWidgets.find((w) => w.name === name);
}
