/**
 * PortfolioCard — Tambo Generative UI Component (exec-09 Phase 2.1)
 *
 * Agent generiert Portfolio-Übersicht via Tool-Call.
 */

import { z } from "zod";

const positionSchema = z.object({
	symbol: z.string(),
	size: z.number(),
	entryPrice: z.number(),
	currentPrice: z.number(),
	pnl: z.number(),
});

export const portfolioCardSchema = z.object({
	totalValue: z.number().describe("Total portfolio value in USD"),
	positions: z.array(positionSchema).describe("Open positions"),
	dayPnl: z.number().optional().describe("Today's P&L"),
});

type PortfolioCardProps = z.infer<typeof portfolioCardSchema>;

export function PortfolioCard({ totalValue, positions, dayPnl }: PortfolioCardProps) {
	const isPositive = (dayPnl ?? 0) >= 0;

	return (
		<div className="rounded-lg border bg-card p-4 space-y-3">
			<div className="flex items-center justify-between">
				<h3 className="text-lg font-semibold">Portfolio</h3>
				<div className="text-right">
					<p className="text-lg font-mono">${totalValue.toLocaleString()}</p>
					{dayPnl != null && (
						<p className={`text-sm font-medium ${isPositive ? "text-green-500" : "text-red-500"}`}>
							{isPositive ? "+" : ""}${dayPnl.toFixed(2)} today
						</p>
					)}
				</div>
			</div>

			{positions.length > 0 && (
				<div className="space-y-2">
					{positions.map((pos) => (
						<div key={pos.symbol} className="flex items-center justify-between text-sm">
							<div>
								<span className="font-medium">{pos.symbol}</span>
								<span className="text-muted-foreground ml-2">×{pos.size}</span>
							</div>
							<span className={pos.pnl >= 0 ? "text-green-500" : "text-red-500"}>
								{pos.pnl >= 0 ? "+" : ""}
								{pos.pnl.toFixed(2)}
							</span>
						</div>
					))}
				</div>
			)}

			{positions.length === 0 && <p className="text-sm text-muted-foreground">No open positions</p>}
		</div>
	);
}
