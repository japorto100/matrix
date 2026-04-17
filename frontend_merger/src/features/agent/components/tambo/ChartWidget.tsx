/**
 * ChartWidget — Tambo Generative UI Component (exec-09 Phase 2.1)
 *
 * Agent generiert dieses Widget via Tool-Call mit Props.
 * Tambo streamt die Props als der LLM sie generiert.
 */

import { z } from "zod";

export const chartWidgetSchema = z.object({
	symbol: z.string().describe("Trading symbol (e.g. EUR/USD, BTC/USD)"),
	timeframe: z.string().describe("Chart timeframe (1m, 5m, 1H, 4H, 1D)"),
	indicators: z.array(z.string()).optional().describe("Active indicators (RSI, MACD, etc.)"),
	price: z.number().optional().describe("Current price"),
	change24h: z.number().optional().describe("24h change percentage"),
});

type ChartWidgetProps = z.infer<typeof chartWidgetSchema>;

export function ChartWidget({ symbol, timeframe, indicators, price, change24h }: ChartWidgetProps) {
	const isPositive = (change24h ?? 0) >= 0;

	return (
		<div className="rounded-lg border bg-card p-4 space-y-3">
			<div className="flex items-center justify-between">
				<div>
					<h3 className="text-lg font-semibold">{symbol}</h3>
					<p className="text-sm text-muted-foreground">{timeframe}</p>
				</div>
				{price != null && (
					<div className="text-right">
						<p className="text-lg font-mono">{price.toFixed(4)}</p>
						{change24h != null && (
							<p
								className={`text-sm font-medium ${isPositive ? "text-green-500" : "text-red-500"}`}
							>
								{isPositive ? "+" : ""}
								{change24h.toFixed(2)}%
							</p>
						)}
					</div>
				)}
			</div>

			{/* Placeholder fuer Chart-Rendering (TradingView Lightweight Charts o.Ae.) */}
			<div className="h-48 rounded bg-muted flex items-center justify-center text-muted-foreground text-sm">
				Chart: {symbol} @ {timeframe}
			</div>

			{indicators && indicators.length > 0 && (
				<div className="flex gap-1.5 flex-wrap">
					{indicators.map((ind) => (
						<span
							key={ind}
							className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium"
						>
							{ind}
						</span>
					))}
				</div>
			)}
		</div>
	);
}
