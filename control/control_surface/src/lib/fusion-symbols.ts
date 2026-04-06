export type FusionSymbolType = "crypto" | "stock" | "fx" | "commodity" | "index" | "macro";

export interface FusionSymbol {
	symbol: string;
	name: string;
	basePrice: number;
	type: FusionSymbolType;
	startYear?: number;
	aliases?: string[];
}

const FUSION_SYMBOLS: FusionSymbol[] = [
	// Crypto
	{
		symbol: "BTC/USD",
		name: "Bitcoin",
		basePrice: 67500,
		type: "crypto",
		startYear: 2010,
		aliases: ["BTC-USD"],
	},
	{
		symbol: "ETH/USD",
		name: "Ethereum",
		basePrice: 3450,
		type: "crypto",
		startYear: 2015,
		aliases: ["ETH-USD"],
	},
	{
		symbol: "SOL/USD",
		name: "Solana",
		basePrice: 178,
		type: "crypto",
		startYear: 2020,
		aliases: ["SOL-USD"],
	},
	{
		symbol: "XRP/USD",
		name: "Ripple",
		basePrice: 0.52,
		type: "crypto",
		startYear: 2013,
		aliases: ["XRP-USD"],
	},
	{
		symbol: "BNB/USD",
		name: "Binance Coin",
		basePrice: 580,
		type: "crypto",
		startYear: 2017,
		aliases: ["BNB-USD"],
	},
	{
		symbol: "ADA/USD",
		name: "Cardano",
		basePrice: 0.45,
		type: "crypto",
		startYear: 2017,
		aliases: ["ADA-USD"],
	},
	{
		symbol: "DOGE/USD",
		name: "Dogecoin",
		basePrice: 0.12,
		type: "crypto",
		startYear: 2014,
		aliases: ["DOGE-USD"],
	},
	{
		symbol: "DOT/USD",
		name: "Polkadot",
		basePrice: 7.2,
		type: "crypto",
		startYear: 2020,
		aliases: ["DOT-USD"],
	},

	// Stocks
	{ symbol: "AAPL", name: "Apple Inc.", basePrice: 189, type: "stock", startYear: 1980 },
	{ symbol: "MSFT", name: "Microsoft Corp.", basePrice: 420, type: "stock", startYear: 1986 },
	{
		symbol: "GOOGL",
		name: "Alphabet Inc.",
		basePrice: 175,
		type: "stock",
		startYear: 2004,
		aliases: ["GOOG"],
	},
	{ symbol: "AMZN", name: "Amazon.com Inc.", basePrice: 185, type: "stock", startYear: 1997 },
	{ symbol: "TSLA", name: "Tesla Inc.", basePrice: 248, type: "stock", startYear: 2010 },
	{ symbol: "NVDA", name: "NVIDIA Corp.", basePrice: 880, type: "stock", startYear: 1999 },
	{ symbol: "META", name: "Meta Platforms Inc.", basePrice: 505, type: "stock", startYear: 2012 },
	{ symbol: "NFLX", name: "Netflix Inc.", basePrice: 605, type: "stock", startYear: 2002 },
	{ symbol: "AMD", name: "Advanced Micro Devices", basePrice: 166, type: "stock", startYear: 1972 },
	{ symbol: "INTC", name: "Intel Corp.", basePrice: 46, type: "stock", startYear: 1971 },
	{ symbol: "CRM", name: "Salesforce Inc.", basePrice: 318, type: "stock", startYear: 2004 },
	{ symbol: "DIS", name: "Walt Disney Co.", basePrice: 104, type: "stock", startYear: 1957 },
	{ symbol: "JPM", name: "JPMorgan Chase & Co.", basePrice: 198, type: "stock", startYear: 1969 },
	{ symbol: "V", name: "Visa Inc.", basePrice: 280, type: "stock", startYear: 2008 },
	{ symbol: "MA", name: "Mastercard Inc.", basePrice: 488, type: "stock", startYear: 2006 },
	{ symbol: "WMT", name: "Walmart Inc.", basePrice: 172, type: "stock", startYear: 1972 },
	{ symbol: "JNJ", name: "Johnson & Johnson", basePrice: 158, type: "stock", startYear: 1944 },
	{ symbol: "PFE", name: "Pfizer Inc.", basePrice: 29, type: "stock", startYear: 1942 },
	{ symbol: "KO", name: "Coca-Cola Co.", basePrice: 64, type: "stock", startYear: 1919 },
	{ symbol: "SAP", name: "SAP SE", basePrice: 175, type: "stock", startYear: 1988 },
	{ symbol: "ASML", name: "ASML Holding", basePrice: 950, type: "stock", startYear: 1995 },

	// Forex
	{
		symbol: "EUR/USD",
		name: "Euro / US Dollar",
		basePrice: 1.085,
		type: "fx",
		startYear: 1999,
		aliases: ["EUR-USD"],
	},
	{
		symbol: "GBP/USD",
		name: "British Pound / US Dollar",
		basePrice: 1.27,
		type: "fx",
		startYear: 1971,
		aliases: ["GBP-USD"],
	},
	{
		symbol: "USD/CHF",
		name: "US Dollar / Swiss Franc",
		basePrice: 0.88,
		type: "fx",
		startYear: 1971,
		aliases: ["USD-CHF"],
	},
	{
		symbol: "USD/JPY",
		name: "US Dollar / Japanese Yen",
		basePrice: 155,
		type: "fx",
		startYear: 1971,
		aliases: ["USD-JPY"],
	},
	{
		symbol: "AUD/USD",
		name: "Australian Dollar / US Dollar",
		basePrice: 0.66,
		type: "fx",
		startYear: 1971,
		aliases: ["AUD-USD"],
	},
	{
		symbol: "USD/CAD",
		name: "US Dollar / Canadian Dollar",
		basePrice: 1.36,
		type: "fx",
		startYear: 1971,
		aliases: ["USD-CAD"],
	},
	{
		symbol: "EUR/CHF",
		name: "Euro / Swiss Franc",
		basePrice: 0.955,
		type: "fx",
		startYear: 1999,
		aliases: ["EUR-CHF"],
	},
	{
		symbol: "GBP/EUR",
		name: "British Pound / Euro",
		basePrice: 1.18,
		type: "fx",
		startYear: 1999,
		aliases: ["GBP-EUR"],
	},

	// Commodities
	{ symbol: "XAU/USD", name: "Gold", basePrice: 2350, type: "commodity", startYear: 1968 },
	{ symbol: "XAG/USD", name: "Silver", basePrice: 28, type: "commodity", startYear: 1968 },
	{ symbol: "CL", name: "Crude Oil WTI", basePrice: 78, type: "commodity", startYear: 1983 },

	// Indices
	{ symbol: "SPX", name: "S&P 500", basePrice: 5200, type: "index", startYear: 1957 },
	{ symbol: "NDX", name: "Nasdaq 100", basePrice: 18100, type: "index", startYear: 1985 },
	{ symbol: "DJI", name: "Dow Jones", basePrice: 39000, type: "index", startYear: 1896 },
	{ symbol: "DAX", name: "DAX 40", basePrice: 18500, type: "index", startYear: 1988 },
	{ symbol: "FTSE", name: "FTSE 100", basePrice: 7700, type: "index", startYear: 1984 },
	{ symbol: "N225", name: "Nikkei 225", basePrice: 38600, type: "index", startYear: 1950 },
	{ symbol: "HSI", name: "Hang Seng Index", basePrice: 16200, type: "index", startYear: 1969 },
	{ symbol: "IXIC", name: "NASDAQ Composite", basePrice: 16500, type: "index", startYear: 1971 },

	// Macro
	{
		symbol: "POLICY_RATE",
		name: "Fed Policy Rate",
		basePrice: 5.25,
		type: "macro",
		startYear: 2008,
	},
	{
		symbol: "IMF_IFS_M_111_FITB",
		name: "USA Policy Rate (IMF)",
		basePrice: 5.25,
		type: "macro",
		startYear: 2000,
	},
	{
		symbol: "CPIAUCSL",
		name: "CPI All Urban (FRED)",
		basePrice: 310,
		type: "macro",
		startYear: 1947,
	},
];

export const ALL_FUSION_SYMBOLS: FusionSymbol[] = FUSION_SYMBOLS;

export const WATCHLIST_CATEGORIES = {
	crypto: FUSION_SYMBOLS.filter((s) => s.type === "crypto"),
	stocks: FUSION_SYMBOLS.filter((s) => s.type === "stock"),
	forex: FUSION_SYMBOLS.filter((s) => s.type === "fx"),
	commodities: FUSION_SYMBOLS.filter((s) => s.type === "commodity"),
	indices: FUSION_SYMBOLS.filter((s) => s.type === "index"),
	macro: FUSION_SYMBOLS.filter((s) => s.type === "macro"),
};

function normalizeForMatch(value: string): string {
	return value.toUpperCase().replace(/-/g, "/").trim();
}

const SYMBOL_ALIAS_LOOKUP: Map<string, string> = (() => {
	const map = new Map<string, string>();
	for (const entry of FUSION_SYMBOLS) {
		map.set(normalizeForMatch(entry.symbol), entry.symbol);
		for (const alias of entry.aliases ?? []) {
			map.set(normalizeForMatch(alias), entry.symbol);
		}
	}
	return map;
})();

export function canonicalizeFusionSymbol(input: string): string {
	const trimmed = input.trim();
	if (!trimmed) return trimmed;
	const normalized = normalizeForMatch(trimmed);
	return SYMBOL_ALIAS_LOOKUP.get(normalized) ?? trimmed;
}

export function resolveFusionSymbol(input: string): FusionSymbol | undefined {
	const canonical = canonicalizeFusionSymbol(input);
	return FUSION_SYMBOLS.find((entry) => entry.symbol === canonical);
}

export function getDefaultStartYear(symbol: FusionSymbol): number {
	if (symbol.startYear && Number.isFinite(symbol.startYear)) {
		return Math.max(1850, Math.floor(symbol.startYear));
	}

	switch (symbol.type) {
		case "crypto":
			return 2010;
		case "fx":
			return 1971;
		case "commodity":
			return 1968;
		case "index":
			return 1950;
		default:
			return 1970;
	}
}

export function searchFusionSymbols(query: string, limit: number = 10): FusionSymbol[] {
	const trimmed = query.trim();
	if (!trimmed) {
		return [];
	}

	const upper = trimmed.toUpperCase();
	const normalized = normalizeForMatch(trimmed);

	return FUSION_SYMBOLS.filter((symbol) => {
		const candidates = [symbol.symbol, symbol.name, ...(symbol.aliases ?? [])];
		return candidates.some((candidate) => {
			const cUpper = candidate.toUpperCase();
			return cUpper.includes(upper) || normalizeForMatch(candidate).includes(normalized);
		});
	}).slice(0, limit);
}
