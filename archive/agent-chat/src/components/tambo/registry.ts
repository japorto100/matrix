/**
 * Tambo Component Registry — exec-09 Phase 2.1
 *
 * Registriert alle Generative UI Components mit JSON Schemas.
 * propsSchema muss ein JSON Schema Objekt sein (nicht Zod direkt).
 */

import type { TamboComponent } from "@tambo-ai/react";
import { ChartWidget } from "./ChartWidget";
import { PortfolioCard } from "./PortfolioCard";

export const tamboComponents: TamboComponent[] = [
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
