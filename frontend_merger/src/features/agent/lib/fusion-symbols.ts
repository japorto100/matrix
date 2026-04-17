/**
 * Stub — FusionSymbol type from main project.
 * Full implementation in tradeview-fusion/src/lib/fusion-symbols.ts
 */

export interface FusionSymbol {
	symbol: string;
	name: string;
	basePrice: number;
	type: "crypto" | "forex" | "stock" | "index" | "commodity";
}
